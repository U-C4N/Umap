"""OSM XML downloads and a single Pyosmium geometry assembly path."""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from pathlib import Path

import osmium
from shapely import from_wkb
from shapely.geometry import mapping

from ..errors import UmapError
from ..models import Dataset, Feature, MapSpec
from .common import Budget, new_client, provider_lock, request_bytes, store_raw, utc_now

GREEN_LANDUSE = {"forest", "grass", "meadow", "recreation_ground", "village_green", "allotments", "cemetery", "orchard", "vineyard"}
GREEN_NATURAL = {"wood", "scrub", "heath", "grassland"}
GREEN_LEISURE = {"park", "garden", "golf_course", "nature_reserve", "recreation_ground"}


def area_layer(tags: dict) -> str | None:
    if tags.get("building") not in {None, "no"}:
        return "buildings"
    if tags.get("natural") == "water" or tags.get("landuse") in {"reservoir", "basin"} or tags.get("waterway") == "riverbank":
        return "water"
    if tags.get("landuse") in GREEN_LANDUSE or tags.get("natural") in GREEN_NATURAL or tags.get("leisure") in GREEN_LEISURE:
        return "green"
    return None


def make_query(bbox: tuple, *, timeout: int = 90) -> str:
    w, s, e, n = bbox
    bounds = f"({s:.9f},{w:.9f},{n:.9f},{e:.9f})"
    selectors = [
        '["building"]["building"!="no"]', '["highway"]', '["natural"="water"]',
        '["waterway"~"^(river|stream|canal|drain|riverbank)$"]',
        '["landuse"~"^(reservoir|basin|forest|grass|meadow|recreation_ground|village_green|allotments|cemetery|orchard|vineyard)$"]',
        '["natural"~"^(wood|scrub|heath|grassland)$"]',
        '["leisure"~"^(park|garden|golf_course|nature_reserve|recreation_ground)$"]',
    ]
    # >> recursively supplies relation members, way members and their nodes.
    body = "".join(f"nwr{selector}{bounds};" for selector in selectors)
    return f"[out:xml][timeout:{max(1, timeout)}][maxsize:157286400];({body});(._;>>;);out meta;"


def validate_xml(path: Path, budget: Budget | None = None) -> tuple[str | None, set[str]]:
    """Reject partial source data before libosmium can quietly skip missing objects."""
    with path.open("rb") as stream:
        previous = b""
        while block := stream.read(64 * 1024):
            if budget:
                budget.remaining()
            data = (previous + block).upper()
            if b"<!DOCTYPE" in data or b"<!ENTITY" in data:
                raise UmapError("source_schema", "XML document/entity declarations are not accepted")
            previous = block[-16:]
    ids: dict[str, set[int]] = {"node": set(), "way": set(), "relation": set()}
    refs: dict[str, set[int]] = {"node": set(), "way": set(), "relation": set()}
    expected = set()
    timestamp = None
    root_seen = False
    try:
        for event, element in ET.iterparse(path, events=("start", "end")):
            if not root_seen:
                root_seen = True
                if element.tag != "osm":
                    raise UmapError("source_schema", "Overpass did not return OSM XML")
            if event != "end":
                continue
            tag = element.tag
            if tag == "remark":
                raise UmapError("source_incomplete", "Overpass reported incomplete data",
                                {"remark": (element.text or "")[:1000]})
            if tag == "meta":
                timestamp = element.attrib.get("osm_base")
            if tag in ids:
                if budget:
                    budget.remaining()
                object_id = int(element.attrib["id"])
                ids[tag].add(object_id)
                if tag == "node":
                    lon, lat = float(element.attrib["lon"]), float(element.attrib["lat"])
                    if not (math.isfinite(lon) and math.isfinite(lat) and -180 <= lon <= 180 and -90 <= lat <= 90):
                        raise ValueError("Invalid WGS84 node coordinates")
                if tag == "way":
                    refs["node"].update(int(n.attrib["ref"]) for n in element.findall("nd"))
                if tag == "relation":
                    for member in element.findall("member"):
                        refs[member.attrib["type"]].add(int(member.attrib["ref"]))
                tags = {t.attrib["k"]: t.attrib["v"] for t in element.findall("tag")}
                if area_layer(tags) and (tag == "way" or (tag == "relation" and tags.get("type") in {"multipolygon", "boundary"})):
                    expected.add(f"osm:{tag}/{object_id}")
                element.clear()
    except UmapError:
        raise
    except (ET.ParseError, KeyError, ValueError, OSError) as exc:
        raise UmapError("source_schema", "Malformed OSM XML response") from exc
    for kind in ids:
        missing = refs[kind] - ids[kind]
        if missing:
            raise UmapError("source_incomplete", f"Missing {kind} references in OSM response",
                            {"missing_count": len(missing), "examples": sorted(missing)[:10]})
    return timestamp, expected


def parse_osm(path: Path, bbox: tuple, *, max_features: int = 200_000,
              budget: Budget | None = None) -> Dataset:
    timestamp, expected = validate_xml(path, budget)
    features: dict[str, Feature] = {}
    assembled = set()
    factory = osmium.geom.WKBFactory()

    class Handler(osmium.SimpleHandler):
        def add(self, identity: str, layer: str, wkb: str, properties: dict):
            if budget:
                budget.remaining()
            if len(features) >= max_features and identity not in features:
                raise UmapError("source_too_large", "Maximum feature count exceeded")
            geometry = from_wkb(bytes.fromhex(wkb))
            features[identity] = Feature(id=identity, layer=layer, geometry=mapping(geometry), properties=properties)

        def way(self, way):
            tags = dict(way.tags)
            layer = "roads" if tags.get("highway") else "water" if tags.get("waterway") in {"river", "stream", "canal", "drain"} else None
            if layer:
                if len(way.nodes) < 2 or any(not n.location.valid() for n in way.nodes):
                    raise UmapError("source_incomplete", "A linear OSM feature has missing coordinates",
                                    {"feature_id": f"osm:way/{way.id}"})
                try:
                    self.add(f"osm:way/{way.id}", layer, factory.create_linestring(way), tags)
                except (RuntimeError, ValueError) as exc:
                    raise UmapError("source_geometry", "Could not assemble OSM line", {"osm_id": way.id}) from exc

        def area(self, area):
            tags = dict(area.tags)
            layer = area_layer(tags)
            if layer:
                identity = f"osm:{'way' if area.from_way() else 'relation'}/{area.orig_id()}"
                try:
                    self.add(identity, layer, factory.create_multipolygon(area), tags)
                    assembled.add(identity)
                except (RuntimeError, ValueError) as exc:
                    raise UmapError("source_geometry", "Could not assemble OSM area", {"feature_id": identity}) from exc

    try:
        Handler().apply_file(str(path), locations=True, idx="flex_mem")
    except UmapError:
        raise
    except (RuntimeError, ValueError) as exc:
        raise UmapError("source_geometry", "OSM geometry assembly failed") from exc
    missing = expected - assembled
    if missing:
        raise UmapError("source_incomplete", "Some tagged OSM areas could not be assembled",
                        {"missing_count": len(missing), "examples": sorted(missing)[:10]})
    return Dataset(features=sorted(features.values(), key=lambda f: f.id), bbox=bbox,
                   sources=[{"provider": "overpass", "data_timestamp": timestamp,
                             "license": "ODbL-1.0", "attribution": "© OpenStreetMap contributors",
                             "attribution_url": "https://www.openstreetmap.org/copyright"}])


def fetch_overpass(spec: MapSpec, bbox: tuple, root: Path, budget: Budget) -> Dataset:
    with provider_lock(root, "overpass", budget):
        query = make_query(bbox, timeout=int(min(90, budget.remaining())))
        with new_client() as client:
            raw, _ = request_bytes(client, "POST", spec.source.overpass_url, budget,
                                   data={"data": query}, max_bytes=spec.limits.max_response_bytes)
        saved = store_raw(root, raw, ".osm")
        dataset = parse_osm(Path(saved["path"]), bbox, max_features=spec.limits.max_features, budget=budget)
        dataset.sources[0].update(endpoint=spec.source.overpass_url, accessed_at=utc_now(),
                                  query=query, raw_files=[saved])
        return dataset
