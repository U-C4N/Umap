import json
import socket
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from shapely.geometry import LineString, Polygon, mapping

from umap_art import MapSpec, render
from umap_art.errors import UmapError
from umap_art.geometry import compute_extent
from umap_art.models import Dataset, Feature
from umap_art.service import load_snapshot
from umap_art.storage import atomic_json, digest


@pytest.fixture
def saved_spec(tmp_path):
    spec = MapSpec(
        area={"center": [29.025, 40.985]},
        page={"size": "A4", "dpi": 72},
        title="İstanbul / Çığ / Iİıi",
        formats=["svg", "pdf", "png"],
    )
    extent = compute_extent(spec)
    features = [
        Feature(
            id="synthetic-building",
            layer="buildings",
            geometry=mapping(
                Polygon([(29.024, 40.984), (29.025, 40.984), (29.025, 40.985), (29.024, 40.985)])
            ),
        ),
        Feature(
            id="synthetic-road",
            layer="roads",
            geometry=mapping(LineString([(29.022, 40.983), (29.028, 40.986)])),
            properties={"highway": "primary"},
        ),
    ]
    data = Dataset(
        features=features,
        bbox=extent.bbox,
        sources=[
            {
                "provider": "synthetic",
                "license": "CC0",
                "note": "Invented test geometry, not real map data",
            }
        ],
    )
    path = tmp_path / "input.json"
    atomic_json(
        path,
        {
            "schema_version": "1",
            "dataset_id": digest(data.model_dump(mode="json")),
            "dataset": data.model_dump(mode="json"),
        },
    )
    return spec.model_copy(
        update={"source": spec.source.model_copy(update={"snapshot": str(path), "offline": True})}
    )


def test_offline_three_formats_and_portable_bundle(saved_spec, tmp_path, monkeypatch):
    def forbidden(*a, **kw):
        raise AssertionError("Offline render attempted network access")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    result = render(saved_spec, output_dir=tmp_path / "out")
    assert {a.mime_type for a in result.artifacts} >= {
        "image/png",
        "image/svg+xml",
        "application/pdf",
        "application/zip",
    }
    manifest = json.loads(Path(result.manifest_path).read_text())
    assert manifest["scale_denominator"] == 5000
    assert manifest["fonts"]
    assert all(Path(a.path).is_file() for a in result.artifacts)
    bundle = next(Path(a.path) for a in result.artifacts if a.mime_type == "application/zip")
    with zipfile.ZipFile(bundle) as archive:
        archive.extractall(tmp_path / "portable")
    again = render(tmp_path / "portable" / "recipe.json", output_dir=tmp_path / "repeat")
    assert result.scene_hashes == again.scene_hashes
    assert result.dataset_id == again.dataset_id


def test_palette_change_preserves_snapshot_without_network(saved_spec, tmp_path, monkeypatch):
    first = render(saved_spec, output_dir=tmp_path / "one")
    revised = MapSpec.model_validate_json(Path(first.recipe_path).read_text())
    revised.source.snapshot = first.snapshot_path
    revised.style.layers = {"roads": {"stroke": "#CC2244"}}
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: pytest.fail("Network requested"))
    second = render(revised, output_dir=tmp_path / "two")
    assert first.dataset_id == second.dataset_id
    assert first.scene_hashes != second.scene_hashes


def test_snapshot_tampering_fails(saved_spec):
    path = Path(saved_spec.source.snapshot)
    value = json.loads(path.read_text())
    value["dataset"]["features"][0]["id"] = "tampered"
    atomic_json(path, value)
    with pytest.raises(UmapError) as exc:
        load_snapshot(path)
    assert exc.value.code == "SNAPSHOT_INTEGRITY"


def test_snapshot_cannot_cover_new_larger_page(saved_spec, tmp_path):
    larger = saved_spec.model_copy(
        update={"page": saved_spec.page.model_copy(update={"size": "A3"})}
    )
    with pytest.raises(UmapError) as exc:
        render(larger, output_dir=tmp_path / "out")
    assert exc.value.code == "SNAPSHOT_EXTENT"


def test_cli_equivalence(saved_spec, tmp_path):
    recipe = tmp_path / "map.json"
    recipe.write_text(saved_spec.model_dump_json(), encoding="utf-8")
    direct = render(saved_spec, output_dir=tmp_path / "direct")
    command = subprocess.run(
        [
            sys.executable,
            "-m",
            "umap_art",
            "render",
            str(recipe),
            "--output",
            str(tmp_path / "cli"),
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert command.returncode == 0, command.stderr
    result = json.loads(command.stdout)
    assert result["scene_hashes"] == direct.scene_hashes
    assert result["dataset_id"] == direct.dataset_id


def test_invalid_recipe_schema_rejected():
    with pytest.raises(ValueError):
        MapSpec(area={"center": [29, 41]}, schema_version="99")


def test_snapshot_obeys_feature_budget(saved_spec, tmp_path):
    saved_spec.limits.max_features = 1
    with pytest.raises(UmapError) as exc:
        render(saved_spec, output_dir=tmp_path / "out")
    assert exc.value.code == "FEATURE_LIMIT"


def test_empty_render_cache_index_is_rebuilt(saved_spec, tmp_path, monkeypatch):
    first = render(saved_spec, output_dir=tmp_path / "first")
    for entry in (tmp_path / "cache" / "renders").rglob("artifacts.json"):
        entry.write_text("[]", encoding="utf-8")
    import umap_art.renderer as renderer

    actual = renderer.render_scene
    calls = []

    def tracked(*args, **kwargs):
        calls.append(True)
        return actual(*args, **kwargs)

    monkeypatch.setattr(renderer, "render_scene", tracked)
    second = render(saved_spec, output_dir=tmp_path / "second")
    assert calls
    assert len(first.artifacts) == len(second.artifacts)
    assert {a.mime_type for a in second.artifacts} >= {
        "image/png",
        "image/svg+xml",
        "application/pdf",
    }


def test_invalid_filter_fails_before_location_lookup(tmp_path, monkeypatch):
    import umap_art.sources as sources

    monkeypatch.setattr(
        sources, "find_locations", lambda *a, **k: pytest.fail("Invalid filter reached network")
    )
    spec = MapSpec(
        area={"place": "Kadıköy"},
        style={
            "rules": [
                {"layer": "roads", "when": {"eval": "anything"}, "paint": {"stroke": "#000000"}}
            ]
        },
    )
    with pytest.raises(UmapError) as exc:
        render(spec, output_dir=tmp_path / "out")
    assert exc.value.code == "INVALID_FILTER"


def test_pinned_source_profile_changes_require_refresh(saved_spec, tmp_path):
    result = render(saved_spec, output_dir=tmp_path / "first")
    saved_spec.source.snapshot = result.snapshot_path
    saved_spec.source.include_ocean = False
    with pytest.raises(UmapError) as exc:
        render(saved_spec, output_dir=tmp_path / "second")
    assert exc.value.code == "SNAPSHOT_SOURCES"
