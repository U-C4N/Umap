"""User-triggered keyless Photon geocoding with persistent rate limiting."""
from __future__ import annotations

import hashlib
import json
import math
import time
from pathlib import Path

from ..errors import UmapError
from .common import Budget, atomic_json, cache_root, new_client, provider_lock, request_bytes

DEFAULT_ENDPOINT = "https://photon.komoot.io"


def parse_locations(payload: dict) -> list[dict]:
    if not isinstance(payload, dict) or not isinstance(payload.get("features"), list):
        raise UmapError("source_schema", "Photon did not return a GeoJSON FeatureCollection")
    results = []
    for feature in payload["features"]:
        try:
            geometry = feature["geometry"]
            coordinates = geometry["coordinates"]
            if geometry["type"] != "Point" or len(coordinates) != 2:
                raise ValueError("Expected point")
            lon, lat = map(float, coordinates)
            if not (math.isfinite(lon) and math.isfinite(lat) and -180 <= lon <= 180 and -90 <= lat <= 90):
                raise ValueError("Coordinates outside WGS84")
            properties = feature["properties"]
            context = {k: properties[k] for k in ("name", "district", "city", "county", "state", "country", "countrycode")
                       if properties.get(k)}
            label = ", ".join(dict.fromkeys(str(v) for k, v in context.items() if k != "countrycode"))
            osm_id = f"{properties.get('osm_type', 'unknown')}/{properties.get('osm_id', '')}"
            stable = json.dumps([osm_id, lon, lat], separators=(",", ":"))
            result = {"candidate_id": hashlib.sha256(stable.encode()).hexdigest()[:20],
                      "label": label or f"{lon}, {lat}", "center": [lon, lat], "provider": "photon",
                      "osm_id": osm_id, "context": context}
            if properties.get("extent") is not None:
                # Photon extent is [minLon, maxLat, maxLon, minLat].
                w, n, e, s = map(float, properties["extent"])
                if not (-180 <= w <= e <= 180 and -90 <= s <= n <= 90):
                    raise ValueError("Invalid Photon extent")
                result["bbox"] = [w, s, e, n]
            results.append(result)
        except (KeyError, TypeError, ValueError) as exc:
            raise UmapError("source_schema", "Photon returned an invalid location") from exc
    return results


def find_locations(query: str, *, cache_dir: Path | None = None, endpoint: str = DEFAULT_ENDPOINT,
                   country_code: str | None = None, bias: tuple | None = None) -> list[dict]:
    if not query.strip() or len(query) > 300:
        raise UmapError("invalid_query", "Enter a place name between 1 and 300 characters")
    params = {"q": query.strip(), "limit": 5}
    if country_code:
        params["countrycode"] = country_code.upper()
    if bias is not None:
        if len(bias) != 2 or not (-180 <= bias[0] <= 180 and -90 <= bias[1] <= 90):
            raise UmapError("invalid_query", "Location bias must be longitude, latitude")
        params.update(lon=bias[0], lat=bias[1])
    root = cache_root(cache_dir)
    key = hashlib.sha256(json.dumps([endpoint, params], sort_keys=True).encode()).hexdigest()
    cached_path = root / "geocoding" / f"{key}.json"
    budget = Budget(30, 2 * 1024**2)
    with provider_lock(root, "photon", budget):
        if cached_path.exists():
            try:
                cached = json.loads(cached_path.read_text(encoding="utf-8"))
                if 0 <= time.time() - cached["stored_at"] < 30 * 86400:
                    return parse_locations(cached["response"])
            except (ValueError, KeyError, OSError, UmapError):
                pass
        timestamp_path = root / "locks" / "photon.last"
        try:
            delay = max(0, 1 - (time.time() - float(timestamp_path.read_text())))
        except (OSError, ValueError):
            delay = 0
        if delay:
            time.sleep(min(delay, budget.remaining()))
        timestamp_path.write_text(str(time.time()), encoding="ascii")
        with new_client() as client:
            raw, _ = request_bytes(client, "GET", endpoint.rstrip("/") + "/api/", budget,
                                   params=params, max_bytes=2 * 1024**2)
        try:
            response = json.loads(raw)
        except ValueError as exc:
            raise UmapError("source_schema", "Photon returned malformed JSON") from exc
        results = parse_locations(response)
        atomic_json(cached_path, {"stored_at": time.time(), "response": response})
        return results
