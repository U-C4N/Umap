"""The distributed real example must be portable, honest and hash-verifiable."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

from umap_art.geometry import compute_extent, prepare_geometry
from umap_art.models import Dataset, MapSpec
from umap_art.scene import compile_scene
from umap_art.service import load_snapshot
from umap_art.storage import digest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "src/umap_art/examples/kadikoy"
MODULE = importlib.util.spec_from_file_location("prepare_demo", ROOT / "scripts/prepare_demo.py")
prepare = importlib.util.module_from_spec(MODULE)
MODULE.loader.exec_module(prepare)


def values(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from values(item)
    elif isinstance(value, list):
        for item in value:
            yield from values(item)
    else:
        yield value


def test_distributed_snapshot_retains_provenance_without_host_paths():
    envelope = json.loads((EXAMPLE / "snapshot.json").read_text(encoding="utf-8"))
    data, identity = load_snapshot(EXAMPLE / "snapshot.json")
    assert identity == envelope["dataset_id"]
    assert data.coverage == "not_assessed"
    assert not any(prepare.is_local_path(value) for value in values(envelope))
    assert {s["provider"] for s in data.sources} == {"overpass", "overture"}
    for source in data.sources:
        assert source["license"] == "ODbL-1.0"
        assert source["endpoint"].startswith("https://")
        assert source["accessed_at"] and source["data_timestamp"]
        assert all(raw["sha256"] and "path" not in raw for raw in source["raw_files"])
    assert "ODbL-1.0" in (EXAMPLE / "DATA-LICENSES.txt").read_text(encoding="utf-8")


@pytest.mark.parametrize("preset", ["poster", "guide", "atlas"])
def test_preset_fits_snapshot_and_has_clean_visible_content(preset):
    spec = MapSpec.model_validate_json((EXAMPLE / f"{preset}.json").read_text(encoding="utf-8"))
    data, _ = load_snapshot(EXAMPLE / "snapshot.json")
    extent = compute_extent(spec)
    w, s, e, n = data.bbox
    qw, qs, qe, qn = extent.bbox
    assert w <= qw <= qe <= e and s <= qs <= qn <= n
    assert spec.source.offline and spec.source.snapshot == "snapshot.json"
    assert spec.page.size == "A4" and spec.page.orientation == "portrait"
    assert spec.page.dpi == 300 and extent.scale_denominator == 5000
    assert spec.formats == ["png", "svg", "pdf"] and spec.bundle
    prepared = prepare_geometry(data, spec, extent)
    for view in spec.views:
        scene = compile_scene(prepared, spec, view)
        assert not scene.diagnostics


def test_poster_and_guide_share_user_selections_and_atlas_is_analytical():
    presets = {p: json.loads((EXAMPLE / f"{p}.json").read_text(encoding="utf-8"))
               for p in ("poster", "guide", "atlas")}
    assert presets["poster"]["places"] == presets["guide"]["places"]
    assert len(presets["poster"]["places"]) == 3
    assert presets["atlas"]["places"] == []
    assert presets["atlas"]["views"] == ["figure_ground", "roads", "green", "water"]


def test_sanitizer_preserves_sources_and_rehashes_only_verified_content():
    dataset = Dataset(bbox=[29, 40, 30, 41], sources=[{
        "provider": "overpass", "endpoint": "https://example.org/api",
        "accessed_at": "2026-10-12", "raw_files": [
            {"path": "C:\\Users\\name\\data.osm", "sha256": "abc", "size_bytes": 12},
            {"path": "/home/name/data.osm", "url": "https://example.org/data", "sha256": "def"},
        ],
    }]).model_dump(mode="json")
    original = {"schema_version": "1", "dataset": dataset, "dataset_id": digest(dataset)}
    clean = prepare.sanitize_snapshot(original)
    assert clean["dataset_id"] != original["dataset_id"]
    assert clean["dataset_id"] == digest(clean["dataset"])
    assert "path" in original["dataset"]["sources"][0]["raw_files"][0]
    assert clean["dataset"]["sources"][0]["raw_files"] == [
        {"sha256": "abc", "size_bytes": 12},
        {"url": "https://example.org/data", "sha256": "def"},
    ]
    corrupt = copy.deepcopy(original)
    corrupt["dataset"]["bbox"][0] = 28
    with pytest.raises(ValueError, match="hash"):
        prepare.sanitize_snapshot(corrupt)
