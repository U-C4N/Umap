"""Narrow, keyless STAC/GeoParquet ocean adapter with bounded HTTP range reads.

The STAC index is metadata, not the global water dataset. Missing index/row-group
statistics are errors: this adapter never falls back to scanning a whole release.
"""
from __future__ import annotations

import io
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from shapely import from_wkb
from shapely.geometry import box, mapping

from ..errors import UmapError
from ..models import Dataset, Feature, MapSpec
from .common import Budget, new_client, provider_lock, request_bytes, store_raw, utc_now

MAX_FILES = 32
MAX_ROW_GROUPS = 128
MAX_DECODED_BYTES = 256 * 1024**2


def overlaps(a: tuple, b: tuple) -> bool:
    return a[0] <= b[2] and a[2] >= b[0] and a[1] <= b[3] and a[3] >= b[1]


def file_url(asset: dict) -> str:
    try:
        aws = asset["aws"]
        href = aws.get("href", "")
        if href.startswith("https://"):
            return href
        href = aws.get("alternate", {}).get("s3", {}).get("href", href)
        if href.startswith("s3://"):
            parsed = urlparse(href)
            return f"https://{parsed.netloc}.s3.us-west-2.amazonaws.com{parsed.path}"
    except (TypeError, KeyError):
        pass
    raise UmapError("source_schema", "Overture STAC asset has no supported anonymous HTTPS/S3 location")


class HTTPRangeReader(io.RawIOBase):
    """Seekable file for PyArrow; persist exactly the requested compressed ranges."""
    def __init__(self, client: httpx.Client, url: str, root: Path, budget: Budget):
        super().__init__()
        self.client, self.url, self.root, self.budget = client, url, root, budget
        self.position = 0
        self.ranges: dict[tuple[int, int], dict] = {}
        raw, headers = request_bytes(client, "GET", url, budget, headers={"Range": "bytes=0-7"}, max_bytes=8)
        match = re.fullmatch(r"bytes 0-7/(\d+)", headers.get("content-range", ""))
        if headers["status"] != 206 or not match or len(raw) != 8 or raw[:4] != b"PAR1":
            raise UmapError("source_schema", "Overture asset must support HTTP ranges and contain Parquet")
        self.length = int(match.group(1))
        self.ranges[(0, 8)] = self._persist(raw, 0, 8)

    def _persist(self, data: bytes, start: int, end: int) -> dict:
        return {**store_raw(self.root, data, ".range"), "url": self.url, "start": start, "end_exclusive": end}

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset: int, whence: int = 0):
        position = offset if whence == 0 else self.position + offset if whence == 1 else self.length + offset if whence == 2 else -1
        if position < 0:
            raise ValueError("Invalid seek")
        self.position = position
        return position

    def read(self, size: int = -1):
        if self.closed:
            raise ValueError("Read of closed range reader")
        self.budget.remaining()
        start = self.position
        end = self.length if size < 0 else min(self.length, start + size)
        if end <= start:
            return b""
        for (cached_start, cached_end), record in self.ranges.items():
            if cached_start <= start and cached_end >= end:
                data = Path(record["path"]).read_bytes()[start - cached_start:end - cached_start]
                self.position = end
                return data
        if end - start > self.budget.max_bytes - self.budget.bytes_read:
            raise UmapError("source_too_large", "Requested Parquet range exceeds remaining byte budget")
        data, headers = request_bytes(self.client, "GET", self.url, self.budget,
                                      headers={"Range": f"bytes={start}-{end - 1}"}, max_bytes=end-start)
        if headers["status"] != 206 or headers.get("content-range") != f"bytes {start}-{end - 1}/{self.length}" or len(data) != end-start:
            raise UmapError("source_schema", "Provider returned an incorrect Parquet byte range")
        self.ranges[(start, end)] = self._persist(data, start, end)
        self.position = end
        return data

    def readinto(self, target):
        data = self.read(len(target))
        target[:len(data)] = data
        return len(data)


def select_assets(index: bytes, bbox: tuple) -> list[str]:
    try:
        metadata = pq.read_metadata(io.BytesIO(index))
        if metadata.num_rows > 1_000_000 or sum(metadata.row_group(i).total_byte_size
                                                for i in range(metadata.num_row_groups)) > 128 * 1024**2:
            raise UmapError("source_too_large", "Overture STAC metadata exceeds its processing budget")
        table = pq.read_table(io.BytesIO(index), columns=["collection", "type", "bbox", "assets"])
        w, s, e, n = bbox
        expression = ((pc.field("collection") == "water") & (pc.field("type") == "Feature")
                      & (pc.field("bbox", "xmin") <= e) & (pc.field("bbox", "xmax") >= w)
                      & (pc.field("bbox", "ymin") <= n) & (pc.field("bbox", "ymax") >= s))
        assets = table.filter(expression)["assets"].to_pylist()
        if len(assets) > MAX_FILES:
            raise UmapError("source_too_large", "Too many Overture files intersect the requested area")
        return sorted({file_url(asset) for asset in assets})
    except UmapError:
        raise
    except (pa.ArrowException, KeyError, TypeError, ValueError) as exc:
        raise UmapError("source_schema", "Overture STAC index schema is unsupported") from exc


def row_group_bounds(group) -> tuple:
    stats = {group.column(i).path_in_schema: group.column(i).statistics for i in range(group.num_columns)}
    names = ("bbox.xmin", "bbox.ymin", "bbox.xmax", "bbox.ymax")
    if any(name not in stats or stats[name] is None or not stats[name].has_min_max for name in names):
        raise UmapError("source_schema", "Overture row groups lack required bbox statistics")
    return stats[names[0]].min, stats[names[1]].min, stats[names[2]].max, stats[names[3]].max


def fetch_ocean(spec: MapSpec, bbox: tuple, root: Path, budget: Budget) -> Dataset:
    records = []
    features: dict[str, Feature] = {}
    selected_groups = 0
    decoded_bytes = 0
    with provider_lock(root, "overture", budget), new_client() as client:
        raw_catalog, _ = request_bytes(client, "GET", spec.source.overture_catalog_url, budget, max_bytes=2 * 1024**2)
        records.append(store_raw(root, raw_catalog, ".json"))
        try:
            catalog = json.loads(raw_catalog)
            release = catalog["latest"]
            if not isinstance(release, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}\.\d+", release):
                raise ValueError("Invalid release")
            links = [link["href"] for link in catalog["links"] if link.get("rel") == "child" and
                     urlparse(link.get("href", "")).path.rstrip("/").endswith(f"/{release}/catalog.json")]
            if len(links) != 1:
                raise ValueError("Missing unambiguous latest release link")
            release_url = urljoin(spec.source.overture_catalog_url, links[0])
            index_url = urljoin(release_url, "collections.parquet")
        except (KeyError, TypeError, ValueError) as exc:
            raise UmapError("source_schema", "Overture catalog has no supported latest release") from exc
        index, _ = request_bytes(client, "GET", index_url, budget, max_bytes=64 * 1024**2)
        records.append(store_raw(root, index, ".parquet"))
        urls = select_assets(index, bbox)
        selection = box(*bbox)
        for url in urls:
            budget.remaining()
            try:
                with HTTPRangeReader(client, url, root, budget) as remote:
                    parquet = pq.ParquetFile(remote, pre_buffer=False)
                    if not {"id", "geometry", "bbox", "subtype"}.issubset(parquet.schema_arrow.names):
                        raise UmapError("source_schema", "Overture water file lacks required columns")
                    for index in range(parquet.num_row_groups):
                        budget.remaining()
                        group = parquet.metadata.row_group(index)
                        if not overlaps(row_group_bounds(group), bbox):
                            continue
                        selected_groups += 1
                        # Bound decoded column data before decompressing the row group.
                        selected_columns = [group.column(c) for c in range(group.num_columns)
                                            if group.column(c).path_in_schema.split(".")[0] in {"id", "geometry", "bbox", "subtype"}]
                        decoded_bytes += sum(c.total_uncompressed_size for c in selected_columns)
                        if selected_groups > MAX_ROW_GROUPS or decoded_bytes > MAX_DECODED_BYTES:
                            raise UmapError("source_too_large", "Overture row-group processing budget exceeded")
                        rows = parquet.read_row_group(index, columns=["id", "geometry", "bbox", "subtype"], use_threads=False)
                        for row in rows.to_pylist():
                            if row["subtype"] != "ocean":
                                continue
                            bounds = row["bbox"]
                            if not overlaps((bounds["xmin"], bounds["ymin"], bounds["xmax"], bounds["ymax"]), bbox):
                                continue
                            geometry = from_wkb(row["geometry"])
                            if geometry.geom_type not in {"Polygon", "MultiPolygon"}:
                                raise UmapError("source_schema", "Overture ocean feature is not polygonal")
                            if not geometry.intersects(selection):
                                continue
                            identity = "overture:" + str(row["id"])
                            features[identity] = Feature(id=identity, layer="water", geometry=mapping(geometry),
                                                          properties={"subtype": "ocean"})
                            if len(features) > spec.limits.max_features:
                                raise UmapError("source_too_large", "Maximum feature count exceeded")
                    records.extend(remote.ranges.values())
            except UmapError:
                raise
            except (pa.ArrowException, ValueError, TypeError, KeyError, OSError) as exc:
                raise UmapError("source_schema", "Could not decode the selected Overture water data") from exc
    return Dataset(bbox=bbox, features=sorted(features.values(), key=lambda f: f.id), sources=[{
        "provider": "overture", "endpoint": spec.source.overture_catalog_url, "release": release,
        "accessed_at": utc_now(), "license": "ODbL-1.0", "attribution": "Overture Maps Foundation; © OpenStreetMap contributors",
        "attribution_url": "https://docs.overturemaps.org/attribution/", "raw_files": records,
        "selected_files": len(urls), "selected_row_groups": selected_groups,
        "decoded_column_bytes": decoded_bytes, "data_timestamp": release,
    }])
