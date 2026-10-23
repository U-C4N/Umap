"""Offline, reproducible 10,000-building/2,000-road service benchmark.

Run ``python scripts/benchmark.py --output .cache/benchmark`` from the checkout.
Each invocation creates an isolated run directory, so the first export is cold.
Generation and process startup are excluded from timing. The cold export includes
first-use renderer imports, geometry preparation, all three 300 DPI formats and
the project ZIP. The 72 DPI preview has warm geometry but no cached raster;
the following cached-preview phase measures reuse of that exact raster. The last
phase changes only road colour and must produce a new preview without networking.
Two additional phases measure a new poster frame with twelve places (including
geometry preparation, reported without a warm-preview time target), then an
accent/order edit on that poster with the existing five-second preview target.

Peak RSS samples this process and its children every 20 ms; this is a sampled
high-water mark, not a guarantee that every instantaneous memory peak is captured.
The report identifies actual machine resources; it does not pretend to execute on
the planned 4-core/16-GiB reference machine.
"""
from __future__ import annotations

import argparse
import gc
import importlib.metadata
import json
import os
import platform
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import psutil
from pyproj import Transformer
from shapely.geometry import LineString, box, mapping
from shapely.ops import transform

from umap_art import MapSpec, render
from umap_art.geometry import compute_extent
from umap_art.models import Dataset, Feature
from umap_art.storage import atomic_json, digest


def synthetic_snapshot(run_dir: Path) -> tuple[MapSpec, dict]:
    spec = MapSpec(area={"center": [29.022, 40.992], "scale_denominator": 14_000},
                   page={"size": "A3", "orientation": "landscape", "dpi": 300},
                   source={"offline": True, "include_ocean": False},
                   title="Synthetic benchmark — 10,000 buildings / 2,000 roads",
                   language="en")
    extent = compute_extent(spec)
    xmin, ymin, xmax, ymax = extent.bounds
    # Leave a 5% border, ensuring all fixture features remain inside the map.
    dx, dy = (xmax-xmin)*0.9/100, (ymax-ymin)*0.9/100
    x0, y0 = xmin+(xmax-xmin)*0.05, ymin+(ymax-ymin)*0.05
    inverse = Transformer.from_crs(extent.crs, "EPSG:4326", always_xy=True)

    def geographic(geometry):
        return mapping(transform(inverse.transform, geometry))

    features = []
    for row in range(100):
        for column in range(100):
            x, y = x0+column*dx, y0+row*dy
            features.append(Feature(id=f"synthetic:building/{row*100+column:05d}",
                layer="buildings", properties={"building": "yes"},
                geometry=geographic(box(x+0.2*dx,y+0.2*dy,x+0.8*dx,y+0.8*dy))))
    for orientation in range(2):
        for lane in range(20):
            for segment in range(50):
                index = orientation*1000 + lane*50 + segment
                if orientation == 0:
                    start = x0+2*segment*dx, y0+5*lane*dy
                    end = x0+(2*segment+1.8)*dx, start[1]
                else:
                    start = x0+5*lane*dx, y0+2*segment*dy
                    end = start[0], y0+(2*segment+1.8)*dy
                features.append(Feature(id=f"synthetic:road/{index:05d}", layer="roads",
                    properties={"highway": "primary" if lane % 5 == 0 else "residential"},
                    geometry=geographic(LineString([start, end]))))
    dataset = Dataset(features=features, bbox=extent.bbox, sources=[{
        "provider": "synthetic", "license": "CC0-1.0", "fixture_version": "1",
        "description": "Deterministic generated geometry; no real map data was downloaded",
    }])
    identity = digest(dataset.model_dump(mode="json"))
    path = run_dir / "input-snapshot.json"
    atomic_json(path, {"schema_version": "1", "dataset_id": identity,
                      "dataset": dataset.model_dump(mode="json")})
    spec.source.snapshot = str(path.resolve())
    return spec, {"dataset_id": identity, "buildings": 10_000, "roads": 2_000,
                  "fixture_version": "1", "frame_area_km2": (xmax-xmin)*(ymax-ymin)/1e6,
                  "bbox": extent.bbox, "snapshot_path": str(path.resolve())}


def measure(name, spec, output_dir, time_target=None):
    process = psutil.Process()
    stopped = threading.Event()
    peak = process.memory_info().rss
    baseline = peak

    def sample():
        nonlocal peak
        while not stopped.is_set():
            rss = 0
            for child in [process, *process.children(recursive=True)]:
                try:
                    rss += child.memory_info().rss
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            peak = max(peak, rss)
            stopped.wait(0.02)

    thread = threading.Thread(target=sample, name="benchmark-memory-sampler", daemon=True)
    thread.start()
    started = time.perf_counter()
    try:
        # The public service gets a pinned, offline snapshot. This additional guard
        # fails conspicuously if an HTTP implementation attempts a new connection.
        with (patch("socket.create_connection", side_effect=RuntimeError("Benchmark networking disabled")),
              patch("socket.socket.connect", side_effect=RuntimeError("Benchmark networking disabled")),
              patch("socket.socket.connect_ex", side_effect=RuntimeError("Benchmark networking disabled")),
              patch("socket.getaddrinfo", side_effect=RuntimeError("Benchmark networking disabled"))):
            result = render(spec, output_dir=output_dir)
        elapsed = time.perf_counter()-started
    finally:
        stopped.set()
        thread.join()
    record = {
        "phase": name, "elapsed_seconds": elapsed, "peak_rss_bytes": peak,
        "baseline_rss_bytes": baseline, "sample_interval_seconds": 0.02,
        "formats": spec.formats, "dpi": spec.page.dpi,
        "scene_hashes": result.scene_hashes, "manifest": result.manifest_path,
        "artifacts": [{"path": a.path, "bytes": a.size_bytes, "mime_type": a.mime_type}
                      for a in result.artifacts],
        "targets": {"elapsed_seconds": time_target, "peak_rss_bytes": 2*1024**3},
        "meets_time_target": elapsed <= time_target if time_target is not None else None,
        "meets_memory_target": peak <= 2*1024**3,
    }
    print(json.dumps({k: record[k] for k in ("phase", "elapsed_seconds", "peak_rss_bytes",
                                            "meets_time_target", "meets_memory_target")}), flush=True)
    return record


def meets_targets(records: list[dict]) -> bool:
    """Check measured values, including phases without a timing target."""
    return bool(records) and all(
        record["peak_rss_bytes"] <= record["targets"]["peak_rss_bytes"]
        and (record["targets"]["elapsed_seconds"] is None
             or record["elapsed_seconds"] <= record["targets"]["elapsed_seconds"])
        for record in records
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(".cache/benchmark"))
    parser.add_argument("--check", action="store_true",
                        help="Exit unsuccessfully if any measured time or memory target fails")
    args = parser.parse_args(argv)
    run_dir = args.output.resolve() / uuid.uuid4().hex
    run_dir.mkdir(parents=True)
    old_cache = os.environ.get("UMAP_CACHE_DIR")
    os.environ["UMAP_CACHE_DIR"] = str(run_dir / "cache")
    try:
        spec, fixture = synthetic_snapshot(run_dir)
        gc.collect()
        records = [measure("cold_final_export", spec, run_dir / "cold-final", 30)]
        preview = spec.model_copy(deep=True)
        preview.formats = ["png"]
        preview.page.dpi = 72
        preview.bundle = False
        records.append(measure("warm_geometry_preview", preview, run_dir / "warm-preview", 5))
        records.append(measure("cached_preview", preview, run_dir / "cached-preview", 5))
        changed = preview.model_copy(deep=True)
        changed.style.layers["roads"] = {"stroke": "#BD4932"}
        records.append(measure("style_change_preview", changed, run_dir / "style-preview", 5))
        poster = preview.model_copy(deep=True)
        poster.page.layout = "poster"
        poster.style.theme = "neon"
        poster.title = "İstanbul — seçtiğim yerler"
        poster.subtitle = "Synthetic poster benchmark"
        poster_extent = compute_extent(poster)
        west, south, east, north = poster_extent.bounds
        inverse = Transformer.from_crs(poster_extent.crs, "EPSG:4326", always_xy=True)
        raw = poster.model_dump(mode="json")
        raw["places"] = [{"id": f"place-{i}", "label": f"Place {i+1}", "coordinates":
            inverse.transform(west+(east-west)*(0.3+0.4*(i//6)),
                              south+(north-south)*(0.15+0.14*(i % 6)))} for i in range(12)]
        poster = MapSpec.model_validate(raw)
        records.append(measure("poster_12_places_preview", poster, run_dir / "poster-preview", None))
        poster.style.accent = "#FFE09A"
        poster.places.reverse()
        records.append(measure("poster_places_edit_preview", poster, run_dir / "places-preview", 5))
        report = {
            "schema_version": "1", "created_at": datetime.now(timezone.utc).isoformat(),
            "network": "disabled; synthetic pinned snapshot", "fixture": fixture,
            "machine": {"os": platform.platform(), "architecture": platform.machine(),
                        "processor": platform.processor(), "python": platform.python_version(),
                        "physical_cores": psutil.cpu_count(logical=False),
                        "logical_cores": psutil.cpu_count(logical=True),
                        "total_memory_bytes": psutil.virtual_memory().total},
            "versions": {name: importlib.metadata.version(name) for name in
                         ["umap-art", "shapely", "pyproj", "matplotlib", "psutil"]},
            "method": __doc__, "phases": records,
            "style_change_changes_scene_hash": records[3]["scene_hashes"] != records[1]["scene_hashes"],
            "places_edit_changes_scene_hash": records[-1]["scene_hashes"] != records[-2]["scene_hashes"],
            "meets_targets": meets_targets(records),
        }
        report_path = run_dir / "benchmark.json"
        atomic_json(report_path, report)
        atomic_json(args.output.resolve() / "latest.json", {"report": str(report_path)})
        print(json.dumps({"report": str(report_path)}), flush=True)
        return 1 if args.check and not report["meets_targets"] else 0
    finally:
        if old_cache is None:
            os.environ.pop("UMAP_CACHE_DIR", None)
        else:
            os.environ["UMAP_CACHE_DIR"] = old_cache


if __name__ == "__main__":
    raise SystemExit(main())
