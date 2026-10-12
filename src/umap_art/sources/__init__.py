"""Keyless online providers shared by Python, CLI and MCP."""
from pathlib import Path

from ..errors import UmapError
from ..models import Dataset, MapSpec
from .common import Budget, cache_root
from .overpass import fetch_overpass
from .overture import fetch_ocean
from .photon import find_locations

__all__ = ["acquire", "find_locations"]


def acquire(spec: MapSpec, bbox: tuple, *, cache_dir: Path) -> Dataset:
    if spec.source.offline:
        raise UmapError("offline_without_snapshot", "Online acquisition is disabled in offline mode")
    root = cache_root(cache_dir)
    budget = Budget(spec.limits.acquisition_seconds, spec.limits.max_response_bytes)
    dataset = fetch_overpass(spec, bbox, root, budget)
    if spec.source.include_ocean:
        ocean = fetch_ocean(spec, bbox, root, budget)
        dataset.features.extend(ocean.features)
        dataset.sources.extend(ocean.sources)
        dataset.diagnostics.extend(ocean.diagnostics)
    if len(dataset.features) > spec.limits.max_features:
        raise UmapError("source_too_large", "Combined sources exceed maximum feature count")
    dataset.features.sort(key=lambda f: f.id)
    budget.remaining()
    return dataset
