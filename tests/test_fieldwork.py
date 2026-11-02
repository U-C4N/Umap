"""Acceptance checks for CSV imports, A5 guides and repeat photography cards."""
from __future__ import annotations

import json
import math
import zipfile
from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfReader
from test_posters import poster_fixture

from umap_art.cli import main
from umap_art.demo import render_demo
from umap_art.errors import UmapError
from umap_art.models import MapSpec
from umap_art.places import read_places_csv
from umap_art.scene import PT_PER_MM, compile_scene, place_anchors, stable_id
from umap_art.service import render
from umap_art.workspace import Workspace


def test_csv_turkish_headers_bom_quoting_ids_and_validation(tmp_path):
    path = tmp_path / "duraklar.csv"
    header = "ad,enlem,boylam,not\n"
    row = '"İskele, giriş",40.985,29.025,"Çekim, sabah"\n'
    other = "Köşe,40.985,29.025,\n"
    path.write_text(header+row+other, encoding="utf-8-sig")
    first, second = read_places_csv(path)
    assert first.coordinates == (29.025, 40.985) and first.note == "Çekim, sabah"
    path.write_text(header+other+row, encoding="utf-8")
    assert read_places_csv(path) == [second, first]
    for bad in ("X,nan,29,", "X,41,181,", row.strip(), '"Unclosed'):
        path.write_text(header+row+bad, encoding="utf-8")
        with pytest.raises(UmapError) as error:
            read_places_csv(path)
        assert error.value.code == "INVALID_PLACES_CSV" and error.value.details["row"] == 3
    path.write_text(header+"".join(f"Place {i},41,29,\n" for i in range(13)), encoding="utf-8")
    with pytest.raises(UmapError) as error:
        read_places_csv(path)
    assert error.value.details["row"] == 14


def test_twelve_coincident_markers_keep_anchors_and_separate_reproducibly():
    spec, prepared, _ = poster_fixture()
    for place in spec.places:
        place.coordinates = spec.places[0].coordinates
    scene = compile_scene(prepared, spec, "general")
    anchors = place_anchors(prepared, spec)
    leaders = next(g.paths for g in scene.groups if g.id == "place-leaders")
    lines = {p.id: p for p in leaders if p.codes == (1, 2)}
    ends = []
    for place in spec.places:
        start, end = lines[stable_id(place.id, "leader")].vertices
        assert start == anchors[place.id] and end != start
        assert all(math.dist(end, other) > 5*PT_PER_MM for other in ends)
        ends.append(end)
    spec.places.reverse()
    reversed_scene = compile_scene(prepared, spec, "general")
    assert set(next(g.paths for g in reversed_scene.groups if g.id == "place-leaders")) == set(leaders)


def test_pocket_duplex_and_directory_use_imported_places(tmp_path):
    path = tmp_path / "places.csv"
    path.write_text("name,latitude,longitude,note\n" + "".join(
        f"Durak {i:02},40.985,29.025,Kısa not {i:02}\n" for i in range(12)), encoding="utf-8")
    result = render_demo("pocket", places_csv=path, output_dir=tmp_path / "out")
    directory = Path(result.recipe_path).parent
    pages = PdfReader(directory / "pocket-guide.pdf").pages
    assert len(pages) == 2
    assert all(tuple(map(float, p.mediabox[2:])) == pytest.approx((148*PT_PER_MM, 210*PT_PER_MM))
               for p in pages)
    assert "Durak 00" not in pages[0].extract_text()
    text = pages[1].extract_text()
    assert text.index("Durak 00") < text.index("Durak 11") and "Kısa not 11" in text
    assert set(result.scene_hashes) == {"pocket-front", "pocket-back"}
    assert (directory / "pocket-back.svg").is_file() and (directory / "pocket-front.png").is_file()
    with Image.open(directory / "pocket-front.png") as image:
        assert image.size == (2706, 3840)


def test_field_cards_cli_and_relocated_project(tmp_path, capsys):
    photo = tmp_path / "köşe.png"
    Image.new("RGB", (90, 60), "#305784").save(photo)
    path = tmp_path / "stations.csv"
    path.write_text("ad,enlem,boylam,yön,fotoğraf,not\n"
                    "Kuzey,40.985,29.025,0,köşe.png,Balkonu ortala.\n"
                    "Doğu,40.9851,29.0251,90,köşe.png,Kapıyı ortala.\n", encoding="utf-8")
    assert main(["demo", "--preset", "field-cards", "--places-csv", str(path),
                 "--output", str(tmp_path / "out"), "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    directory = Path(result["recipe_path"]).parent
    pages = PdfReader(directory / "field-cards.pdf").pages
    assert len(pages) == 2
    for number, (p, name, bearing) in enumerate(zip(pages, ("Kuzey", "Doğu"), (0, 90)), 1):
        assert tuple(map(float, p.mediabox[2:])) == pytest.approx((148*PT_PER_MM, 210*PT_PER_MM))
        assert name in p.extract_text() and f"{bearing}°" in p.extract_text()
        images_drawn = [args[0] for args, op in p.get_contents().operations if op == b"Do"
                        and p["/Resources"]["/XObject"][args[0]]["/Subtype"] == "/Image"]
        assert len(images_drawn) == 1
        svg = (directory / f"field-card-{number:02}.svg").read_text(encoding="utf-8")
        assert "camera-bearing" in svg and "camera-position" in svg and "data:image/png" in svg
        with Image.open(directory / f"field-card-{number:02}.png") as image:
            assert image.size == (2706, 3840)
    with zipfile.ZipFile(directory / "project.zip") as bundle:
        bundle.extractall(tmp_path / "moved")
        spec = json.loads(bundle.read("recipe.json"))
        assert len({p["reference_photo"] for p in spec["places"]}) == 1
        assert spec["places"][0]["reference_photo"].startswith("photos/")
    photo.unlink()
    reproduced = render(tmp_path / "moved/recipe.json", output_dir=tmp_path / "again")
    assert reproduced.scene_hashes == result["scene_hashes"]
    assert (Path(reproduced.recipe_path).parent / "field-cards.pdf").read_bytes() == (
        directory / "field-cards.pdf").read_bytes()


def test_workspace_bounds_photo_inputs_and_pins_csv_on_create(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    photo = root / "frame.jpg"
    Image.new("RGB", (60, 90), "red").save(photo)
    original = photo.read_bytes()
    path = root / "stations.csv"
    header = "name,latitude,longitude,bearing,reference_photo\n"
    path.write_text(header+"Gate,40.985,29.025,350,frame.jpg\n")
    spec = {"area": {"center": [29.025, 40.985]},
            "page": {"layout": "field_cards", "size": "A5", "orientation": "portrait"}}
    with Workspace(root, start_worker=False) as workspace:
        result = workspace.create_map(spec, places_csv="stations.csv", request_id="import")
        photo.unlink()
        path.unlink()
        assert workspace.create_map(spec, places_csv="stations.csv", request_id="import") == result
        saved = workspace.inspect_map(result["map_id"])["spec"]
        assert Path(saved["places"][0]["reference_photo"]).read_bytes() == original
        path.write_text(header+"Gate,40.985,29.025,90,../outside.jpg\n")
        with pytest.raises(UmapError) as error:
            workspace.create_map(spec, places_csv="stations.csv")
        assert error.value.code == "PATH_OUTSIDE_WORKSPACE"


def test_unreadable_photo_and_missing_bearing_fail_cleanly(tmp_path):
    path = tmp_path / "stations.csv"
    path.write_text("name,latitude,longitude,bearing,reference_photo\n"
                    "Gate,40.985,29.025,90,gone.jpg\n")
    with pytest.raises(UmapError) as error:
        render_demo("field-cards", places_csv=path, output_dir=tmp_path / "out")
    assert error.value.code == "INVALID_REFERENCE_PHOTO" and not list((tmp_path / "out").iterdir())
    with pytest.raises(ValueError, match="bearing"):
        MapSpec(area={"center": [29.025, 40.985]}, page={"size": "A5", "orientation": "portrait",
                "layout": "field_cards"}, places=[{"id": "x", "label": "X", "coordinates": [29, 41]}])
