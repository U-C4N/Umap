"""Poster acceptance: physical outputs, user locations, offline edits and upgrades."""
from __future__ import annotations

import asyncio
import json
import math
import socket
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest
from PIL import Image
from pydantic import ValidationError
from pypdf import PdfReader
from pyproj import Transformer
from test_render import SVG, fixture_scene
from test_workspace import recipe, wait_for

from umap_art.errors import UmapError
from umap_art.geometry import compute_extent
from umap_art.models import MapSpec
from umap_art.renderer import render_scene
from umap_art.scene import PT_PER_MM, compile_scene, stable_id
from umap_art.service import load_snapshot, render
from umap_art.styles import list_styles
from umap_art.workspace import Workspace


def poster_fixture(layout="poster", count=12, **kwargs):
    page = {"size": "A4", "orientation": "portrait", "dpi": 72, "layout": layout}
    page.update(kwargs.pop("page", {}))
    spec, prepared, _ = fixture_scene(page=page, **kwargs)
    spec.title, spec.subtitle = "İstanbul", "Seçtiğim mekânlar · 2026"
    west, south, east, north = prepared.bounds
    inverse = Transformer.from_crs(prepared.crs, "EPSG:4326", always_xy=True)
    raw = spec.model_dump()
    raw["places"] = [{"id": f"place-{i}", "label": f"Çağrı {i+1}", "coordinates":
        inverse.transform(west+(east-west)*(0.3+0.4*(i//6)),
                          south+(north-south)*(0.15+0.14*(i % 6)))} for i in range(count)]
    spec = MapSpec.model_validate(raw)
    return spec, prepared, compile_scene(prepared, spec, "general")


@pytest.mark.parametrize("theme", ["minimal", "blueprint", "vintage", "neon"])
@pytest.mark.parametrize("layout", ["poster", "guide"])
@pytest.mark.parametrize("size,orientation", [("A3", "portrait"), ("A3", "landscape"),
                                             ("A4", "portrait"), ("A4", "landscape")])
def test_layout_matrix_keeps_scale_and_all_places(theme, layout, size, orientation):
    spec, prepared, scene = poster_fixture(layout, style={"theme": theme},
        page={"size": size, "orientation": orientation})
    assert not scene.diagnostics
    assert scene.scale_denominator == 5000
    road = next(p for g in scene.groups for p in g.paths if p.feature_id == "osm/way/2")
    assert math.dist(*road.vertices)/PT_PER_MM == pytest.approx(20, abs=1e-7)
    assert len(next(g for g in scene.groups if g.id == "places").paths) == 12
    initial_bounds = compute_extent(spec).bounds
    spec.places = []
    assert compute_extent(spec).bounds == initial_bounds
    assert compile_scene(prepared, spec, "general").frame == scene.frame


@pytest.mark.parametrize("theme", ["minimal", "blueprint", "vintage", "neon"])
@pytest.mark.parametrize("layout", ["poster", "guide"])
def test_poster_outputs_are_editable_and_physically_scaled(tmp_path, theme, layout):
    spec, _, scene = poster_fixture(layout, style={"theme": theme})
    render_scene(scene, spec, tmp_path)
    root = ET.parse(tmp_path / "general.svg").getroot()
    elements = {element.attrib["id"]: element for element in root.iter() if "id" in element.attrib}
    assert len(elements) == len([element for element in root.iter() if "id" in element.attrib])
    assert elements["title"].find(f"{SVG}text").text == "İstanbul"
    assert elements[stable_id("place-0", "place-label")].find(f"{SVG}text").text == "01  Çağrı 1"
    assert elements[stable_id("place-0", "place-marker")].find(f"{SVG}path") is not None
    assert elements[stable_id("place-0", "place-number")].find(f".//{SVG}text").text == "1"
    assert "image" not in {e.tag.removeprefix(SVG) for e in root.iter()}
    page = PdfReader(tmp_path / "general.pdf").pages[0]
    width, height = spec.page.dimensions_mm
    assert float(page.mediabox.width) == pytest.approx(width*PT_PER_MM, abs=1e-5)
    assert float(page.mediabox.height) == pytest.approx(height*PT_PER_MM, abs=1e-5)
    assert any("/FontFile2" in f.get_object()["/DescendantFonts"][0].get_object()["/FontDescriptor"]
               for f in page["/Resources"]["/Font"].values() if "/DescendantFonts" in f.get_object())
    image = Image.open(tmp_path / "general.png")
    assert image.size == (round(width/25.4*72), round(height/25.4*72))


def test_places_preserve_identity_when_reordered_removed_and_recolored():
    spec, prepared, scene = poster_fixture(count=2)
    spec.places.reverse()
    spec.style.accent = "#CC2244"
    changed = compile_scene(prepared, spec, "general")
    old_markers = {p.id: p for g in scene.groups if g.id == "places" for p in g.paths}
    new_markers = {p.id: p for g in changed.groups if g.id == "places" for p in g.paths}
    assert old_markers.keys() == new_markers.keys()
    assert all(new_markers[k].vertices == v.vertices for k, v in old_markers.items())
    for group in scene.groups:
        if group.id.startswith("layer-"):
            assert group == next(g for g in changed.groups if g.id == group.id)
    number = next(t for t in changed.texts if t.id == stable_id("place-0", "place-number"))
    assert number.text == "2"
    spec.places = spec.places[:1]
    assert len(next(g for g in compile_scene(prepared, spec, "general").groups
                    if g.id == "places").paths) == 1


@pytest.mark.parametrize("places", [
    [{"id": "x", "label": "A", "coordinates": [29, 999]}],
    [{"id": "x", "label": "A", "coordinates": [float("nan"), 41]}],
    [{"id": " ", "label": "A", "coordinates": [29, 41]}],
    [{"id": "x", "label": " ", "coordinates": [29, 41]}],
    [{"id": "x", "label": "A", "coordinates": [29, 41]}]*2,
    [{"id": str(i), "label": "A", "coordinates": [29, 41]} for i in range(13)],
])
def test_invalid_places_are_rejected(places):
    with pytest.raises(ValidationError):
        MapSpec(area={"center": [29, 41]}, page={"layout": "poster"}, places=places)


def test_poster_view_contract_and_style_colors():
    with pytest.raises(ValidationError, match="general"):
        MapSpec(area={"center": [29, 41]}, page={"layout": "guide"}, views=["roads"])
    with pytest.raises(ValidationError, match="Places require"):
        MapSpec(area={"center": [29, 41]}, places=[{"id": "x", "label": "A", "coordinates": [29, 41]}])
    for field in ("ink", "accent"):
        with pytest.raises(ValidationError, match="RRGGBB"):
            MapSpec(area={"center": [29, 41]}, style={field: "red"})
    assert {s["name"] for s in list_styles()} == {
        "architectural", "city_poster", "minimal", "blueprint", "vintage", "neon"}


def test_place_preflight_and_overlap_diagnostics():
    spec, prepared, _ = poster_fixture(count=2)
    spec.places[1].coordinates = spec.places[0].coordinates
    assert "PLACE_OVERLAP" in {d.code for d in compile_scene(prepared, spec, "general").diagnostics}
    spec.places[1].coordinates = (30, 42)
    with pytest.raises(UmapError) as error:
        compile_scene(prepared, spec, "general")
    assert error.value.code == "PLACE_OUTSIDE_MAP"
    spec.places = spec.places[:1]
    for label, code in [("W"*180, "TEXT_OVERFLOW"), ("Two\nlines", "TEXT_OVERFLOW"),
                        ("Unsupported \U0001FAE0", "MISSING_GLYPH")]:
        spec.places[0].label = label
        with pytest.raises(UmapError) as error:
            compile_scene(prepared, spec, "general")
        assert error.value.code == code


def test_typography_is_fixed_and_outline_export_is_supported(tmp_path):
    spec, prepared, original = poster_fixture(count=1)
    spec.page.title_size_pt = 20
    spec.page.subtitle_size_pt = 8
    spec.style.ink = "#345678"
    scene = compile_scene(prepared, spec, "general")
    assert scene.frame == original.frame
    assert next(t for t in scene.texts if t.id == "title").size_pt == 20
    assert next(t for t in scene.texts if t.id == "title").color == "#345678"
    spec.page.text_mode = "outline"
    spec.formats = ["svg"]
    render_scene(scene, spec, tmp_path)
    root = ET.parse(tmp_path / "general.svg").getroot()
    assert not list(root.iter(f"{SVG}text"))
    spec.page.title_size_pt = 48
    with pytest.raises(UmapError) as error:
        compile_scene(prepared, spec, "general")
    assert error.value.code == "TEXT_OVERFLOW"


def test_legacy_layout_defaults_remain_unchanged():
    spec, _, scene = fixture_scene()
    assert spec.page.layout == "classic" and spec.places == []
    assert tuple(v/PT_PER_MM for v in scene.frame) == pytest.approx((10, 26, 400, 241))
    assert next(t for t in scene.texts if t.id == "title").size_pt == 18
    assert next(t for t in scene.texts if t.id == "subtitle").text == "Kent haritası"
    assert next(g for g in scene.groups if g.id == "page").paths[0].paint.fill == "#FFFFFF"


def test_shipped_examples_compile_with_all_places_in_bounds():
    from umap_art.geometry import PreparedGeometry

    for path in (Path(__file__).resolve().parents[1] / "examples").glob("*.json"):
        spec = MapSpec.model_validate_json(path.read_text("utf-8"))
        extent = compute_extent(spec)
        prepared = PreparedGeometry([], extent.crs, extent.bounds,
                                    extent.scale_denominator, [], extent.projection_distortion)
        for view in spec.views:
            compile_scene(prepared, spec, view)


def test_near_edge_place_is_clipped_without_moving(tmp_path):
    spec, prepared, _ = poster_fixture(count=1)
    west, south, east, north = prepared.bounds
    inverse = Transformer.from_crs(prepared.crs, "EPSG:4326", always_xy=True)
    spec.places[0].coordinates = inverse.transform(west+0.001, (south+north)/2)
    scene = compile_scene(prepared, spec, "general")
    assert "PLACE_CLIPPED" in {d.code for d in scene.diagnostics}
    number = next(t for t in scene.texts if t.id == stable_id("place-0", "place-number"))
    assert number.clip and number.x == pytest.approx(scene.frame[0], abs=0.001)
    spec.formats = ["svg"]
    render_scene(scene, spec, tmp_path)
    root = ET.parse(tmp_path / "general.svg").getroot()
    group = next(e for e in root.iter() if e.attrib.get("id") == number.id)
    assert group.find(f"{SVG}g").attrib.get("clip-path")


def test_expanded_page_requires_explicit_refresh_changes(tmp_path):
    from umap_art.storage import atomic_json

    spec = offline_poster(tmp_path)
    dataset, _ = load_snapshot(Path(spec["source"]["snapshot"]))
    dataset.bbox = compute_extent(MapSpec.model_validate(spec)).bbox
    from umap_art.service import _snapshot_id
    atomic_json(Path(spec["source"]["snapshot"]), {"schema_version": "1",
        "dataset_id": _snapshot_id(dataset), "dataset": dataset.model_dump(mode="json")})
    with Workspace(tmp_path, start_worker=False) as workspace:
        created = workspace.create_map(spec)
        with pytest.raises(UmapError) as error:
            workspace.edit_map(created["map_id"], 1, {"page": {"size": "A3"}})
        assert error.value.code == "SNAPSHOT_COVERAGE"
        assert workspace.inspect_map(created["map_id"])["revision"] == 1
        queued = workspace.refresh_map_data(created["map_id"], 1, changes={"page": {"size": "A3"}})
        assert workspace.inspect_map(created["map_id"])["spec"]["page"]["size"] == "A4"
        workspace.cancel_job(queued["job_id"])
        assert workspace.inspect_map(created["map_id"])["revision"] == 1


def offline_poster(root):
    spec = recipe(root)
    spec["page"].update(layout="poster")
    spec["title"] = "İstanbul"
    spec["places"] = [{"id": "home", "label": "Başlangıç", "coordinates": [28.99, 41]}]
    spec["bundle"] = True
    return spec


def test_offline_design_edits_reuse_geometry_and_deliver_portable_recipe(tmp_path, monkeypatch):
    import umap_art.service as service

    spec = offline_poster(tmp_path)
    first = render(spec, output_dir=tmp_path / "first")
    monkeypatch.setattr(socket.socket, "connect", lambda *a, **k: pytest.fail("Network requested"))
    monkeypatch.setattr(service, "prepare_geometry", lambda *a, **k: pytest.fail("Geometry rebuilt"))
    spec["style"].update(theme="neon", accent="#FFAA22")
    spec["places"].append({"id": "second", "label": "İkinci", "coordinates": [28.991, 41]})
    spec["title"] = "Benim İstanbul’um"
    spec["page"]["title_size_pt"] = 20
    second = render(spec, output_dir=tmp_path / "second")
    assert first.dataset_id == second.dataset_id and first.scene_hashes != second.scene_hashes
    assert first.snapshot_path != second.snapshot_path
    manifest = json.loads(Path(second.manifest_path).read_text("utf-8"))
    assert manifest["places"] == spec["places"]
    assert manifest["style"]["theme"] == "neon"
    bundle = Path(second.recipe_path).with_name("project.zip")
    with zipfile.ZipFile(bundle) as archive:
        saved = json.loads(archive.read("recipe.json"))
        assert saved["places"] == spec["places"]
        assert saved["source"]["offline"] and saved["source"]["snapshot"] == "snapshot.json"
        archive.extractall(tmp_path / "relocated")
    reproduced = render(tmp_path / "relocated" / "recipe.json", output_dir=tmp_path / "again")
    assert reproduced.scene_hashes == second.scene_hashes


def test_places_revision_replace_restore_and_refresh_transaction(tmp_path, monkeypatch):
    from umap_art import sources

    with Workspace(tmp_path, start_worker=False) as workspace:
        spec = offline_poster(tmp_path)
        created = workspace.create_map(spec)
        map_id = created["map_id"]
        workspace.cancel_job(created["job_id"])
        removed = workspace.edit_map(map_id, 1, {"places": []})
        assert workspace.inspect_map(map_id)["spec"]["places"] == []
        workspace.cancel_job(removed["job_id"])
        restored = workspace.edit_map(map_id, 2, restore_revision=1)
        assert workspace.inspect_map(map_id)["spec"]["places"] == spec["places"]
        workspace.cancel_job(restored["job_id"])
        changes = {"page": {"size": "A3", "layout": "guide"}, "title": "Yeni"}
        refresh = workspace.refresh_map_data(map_id, 3, request_id="refresh", changes=changes)
        assert workspace.refresh_map_data(map_id, 3, request_id="refresh", changes=changes) == refresh
        with pytest.raises(UmapError, match="different arguments"):
            workspace.refresh_map_data(map_id, 3, request_id="refresh", changes={"title": "Other"})
        assert workspace.inspect_map(map_id)["revision"] == 3
        dataset, _ = load_snapshot(Path(spec["source"]["snapshot"]))
        monkeypatch.setattr(sources, "acquire", lambda *a, **k: dataset)
        job = workspace._db.execute("SELECT * FROM jobs WHERE id=?", (refresh["job_id"],)).fetchone()
        output = tmp_path / "jobs" / refresh["job_id"] / "output"
        result = render(json.loads(job["spec"]), refresh=True, output_dir=output)
        workspace._publish(job, result, output)
        current = workspace.inspect_map(map_id)
        assert current["revision"] == 4
        assert current["spec"]["title"] == "Yeni"
        assert current["spec"]["page"]["layout"] == "guide"
        assert current["spec"]["source"]["offline"]
        with pytest.raises(UmapError) as error:
            workspace.refresh_map_data(map_id, 4, changes={"source": {"photon_url": "http://invalid"}})
        assert error.value.code == "INVALID_EDIT"


def test_failed_refresh_retains_successful_recipe_and_artifacts(tmp_path):
    with Workspace(tmp_path) as workspace:
        created = workspace.create_map(offline_poster(tmp_path))
        assert wait_for(workspace, created["job_id"])["state"] == "succeeded"
        before = workspace.inspect_map(created["map_id"])
        workspace._command = [sys.executable, "-c",
            "import json,sys,pathlib; r=json.loads(sys.stdin.buffer.readline()); "
            "pathlib.Path(r['result_file']).write_text(json.dumps({'error': "
            "{'code':'source_unavailable','message':'Synthetic acquisition failure'}}))"]
        refresh = workspace.refresh_map_data(created["map_id"], 1,
            changes={"page": {"size": "A3"}, "title": "Must not commit"})
        failed = wait_for(workspace, refresh["job_id"])
        assert failed["state"] == "failed" and failed["error"]["code"] == "source_unavailable"
        after = workspace.inspect_map(created["map_id"])
        assert after["revision"] == before["revision"]
        assert after["spec"] == before["spec"]
        assert after["artifacts"] == before["artifacts"]


def test_python_cli_mcp_poster_equivalence(tmp_path):
    pytest.importorskip("mcp")
    from umap_art.mcp_server import create_server

    spec = offline_poster(tmp_path)
    direct = render(spec, output_dir=tmp_path / "python")
    saved = tmp_path / "poster.json"
    saved.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    cli = subprocess.run([sys.executable, "-m", "umap_art", "render", str(saved),
        "--output", str(tmp_path / "cli"), "--json"], capture_output=True,
        text=True, encoding="utf-8", timeout=45)
    assert cli.returncode == 0, cli.stderr
    assert json.loads(cli.stdout)["scene_hashes"] == direct.scene_hashes

    async def scenario():
        server = create_server(tmp_path)
        try:
            created = await server.call_tool("create_map", {"spec": spec})
            assert not created.is_error
            completed = wait_for(server.umap_workspace, created.structured_content["job_id"])
            assert completed["state"] == "succeeded", completed
            assert completed["result"]["scene_hashes"] == direct.scene_hashes
            edited = await server.call_tool("edit_map", {
                "map_id": created.structured_content["map_id"], "base_revision": 1,
                "changes": {"places": [], "style": {"theme": "blueprint"}}})
            assert not edited.is_error
            preview = wait_for(server.umap_workspace, edited.structured_content["job_id"])
            assert preview["state"] == "succeeded", preview
            assert preview["result"]["dataset_id"] == direct.dataset_id
        finally:
            server.umap_workspace.close()
    asyncio.run(scenario())
