"""Output-level acceptance checks for physical layout and editable map delivery."""
from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET

import pytest
from matplotlib import rc_context
from PIL import Image
from pypdf import PdfReader
from shapely.geometry import LineString, Polygon, box, mapping

from umap_art.errors import UmapError
from umap_art.geometry import PreparedGeometry, compute_extent
from umap_art.models import Feature, MapSpec
from umap_art.renderer import _figure, render_scene
from umap_art.scene import PT_PER_MM, compile_scene
from umap_art.styles import list_styles, validate_filter

SVG = "{http://www.w3.org/2000/svg}"


def fixture_scene(**kwargs):
    spec = MapSpec(area={"center": [29, 41], "scale_denominator": 5000},
                   title="İstanbul — Çağrı, Işık ve Şehir", **kwargs)
    extent = compute_extent(spec)
    xmin, ymin, xmax, ymax = extent.bounds
    cx, cy = (xmin+xmax)/2, (ymin+ymax)/2
    building = Polygon([(cx-200,cy-200),(cx+200,cy-200),(cx+200,cy+200),(cx-200,cy+200)],
                       [[(cx-50,cy-50),(cx+50,cy-50),(cx+50,cy+50),(cx-50,cy+50)]])
    geometries = [
        Feature(id="osm/way/1", layer="buildings", geometry=mapping(building)),
        Feature(id="osm/way/2", layer="roads", properties={"highway": "primary"},
                geometry=mapping(LineString([(cx-50, cy+250), (cx+50, cy+250)]))),
        Feature(id="osm/way/3", layer="green", geometry=mapping(box(cx-450,cy-200,cx-300,cy))),
        Feature(id="overture/ocean/1", layer="water", geometry=mapping(box(cx+300,cy-200,cx+450,cy))),
    ]
    prepared = PreparedGeometry(geometries, extent.crs, extent.bounds,
                                extent.scale_denominator, [], extent.projection_distortion)
    return spec, prepared, compile_scene(prepared, spec, "general")


def test_svg_editability_pdf_size_png_dimensions_and_scale(tmp_path):
    spec, _, scene = fixture_scene(page={"size": "A4", "dpi": 150})
    artifacts = render_scene(scene, spec, tmp_path)
    assert len(artifacts) == 3
    assert all(a.size_bytes > 1000 and len(a.sha256) == 64 for a in artifacts)
    root = ET.parse(tmp_path / "general.svg").getroot()
    width, height = spec.page.dimensions_mm
    assert float(root.attrib["width"].removesuffix("pt")) == pytest.approx(width*PT_PER_MM, abs=1e-5)
    assert float(root.attrib["height"].removesuffix("pt")) == pytest.approx(height*PT_PER_MM, abs=1e-5)
    ids = [element.attrib["id"] for element in root.iter() if "id" in element.attrib]
    assert len(ids) == len(set(ids))
    assert {"layer-buildings", "layer-roads", "layer-water", "layer-green", "title", "attribution"} <= set(ids)
    title = next(e for e in root.iter() if e.attrib.get("id") == "title")
    assert title.find(f"{SVG}text").text == spec.title
    attribution = next(t for t in scene.texts if t.id == "attribution")
    assert "openstreetmap.org/copyright" in attribution.text
    assert attribution.size_pt >= 7
    building = next(p for g in scene.groups for p in g.paths if p.feature_id == "osm/way/1")
    building_group = next(e for e in root.iter() if e.attrib.get("id") == building.id)
    assert building_group.find(f"{SVG}path").attrib["d"].count("M ") == 2
    road = next(p for g in scene.groups for p in g.paths if p.feature_id == "osm/way/2")
    length = math.dist(*road.vertices)
    assert length/PT_PER_MM == pytest.approx(20, abs=1e-7)  # 100 m at 1:5000.
    road_group = next(e for e in root.iter() if e.attrib.get("id") == road.id)
    serialized = road_group.find(f"{SVG}path").attrib["d"]
    coordinates = [float(v) for v in re.findall(r"[-+]?\d*\.?\d+(?:e[-+]?\d+)?", serialized)]
    assert math.dist(coordinates[:2], coordinates[2:])/PT_PER_MM == pytest.approx(20, abs=1e-5)
    page = PdfReader(tmp_path / "general.pdf").pages[0]
    assert float(page.mediabox.width) == pytest.approx(width*PT_PER_MM, abs=1e-5)
    assert float(page.mediabox.height) == pytest.approx(height*PT_PER_MM, abs=1e-5)
    # Check the delivered PDF operators, not just the intermediate scene model.
    operations = page.get_contents().operations
    delivered_road = False
    for (start, start_op), (end, end_op) in zip(operations, operations[1:]):
        if start_op == b"m" and end_op == b"l":
            if math.dist(tuple(map(float, start)), road.vertices[0]) < 1e-5:
                assert math.dist(tuple(map(float, end)), road.vertices[1]) < 1e-5
                assert math.dist(start, end)/PT_PER_MM == pytest.approx(20, abs=1e-5)
                delivered_road = True
    assert delivered_road
    fonts = page["/Resources"]["/Font"]
    assert any("/FontFile2" in font.get_object()["/DescendantFonts"][0].get_object()["/FontDescriptor"]
               for font in fonts.values() if "/DescendantFonts" in font.get_object())
    image = Image.open(tmp_path / "general.png")
    assert image.size == (round(width/25.4*150), round(height/25.4*150))


def test_polygon_hole_is_background_in_raster(tmp_path):
    spec, _, scene = fixture_scene(formats=["png"], page={"size": "A4", "dpi": 100})
    render_scene(scene, spec, tmp_path)
    image = Image.open(tmp_path / "general.png").convert("RGB")
    x, y, w, h = scene.frame
    center = (round((x+w/2)/scene.width_pt*image.width),
              round((scene.height_pt-y-h/2)/scene.height_pt*image.height))
    assert image.getpixel(center) == (250, 250, 247)
    # A point 100 m east of the centre lies in the wall, outside the courtyard.
    wall = (round(center[0] + 100/scene.scale_denominator*1000/25.4*100), center[1])
    assert image.getpixel(wall) == (69, 74, 79)


def test_targeted_style_edit_retains_other_layers_geometry_and_ids():
    spec, prepared, original = fixture_scene()
    edited = spec.model_copy(deep=True)
    edited.style.layers["roads"] = {"stroke": "#FF0000", "width_mm": 0.5}
    result = compile_scene(prepared, edited, "general")
    assert result.semantic_hash() != original.semantic_hash()
    old = {p.id: p for g in original.groups for p in g.paths}
    new = {p.id: p for g in result.groups for p in g.paths}
    assert old.keys() == new.keys()
    for identifier, old_path in old.items():
        assert old_path.vertices == new[identifier].vertices
        if "roads" not in identifier:
            assert old_path == new[identifier]
    assert original.semantic_hash() == compile_scene(prepared, spec, "general").semantic_hash()


def test_four_views_have_identical_extent_and_physical_control_points():
    spec, prepared, _ = fixture_scene()
    scenes = [compile_scene(prepared, spec, v) for v in ("figure_ground", "roads", "green", "water")]
    assert len({s.frame for s in scenes}) == 1
    assert len({s.scale_denominator for s in scenes}) == 1
    assert len({(s.width_pt, s.height_pt) for s in scenes}) == 1
    for scene, layer in zip(scenes, ("buildings", "roads", "green", "water")):
        assert [g.id for g in scene.groups if g.id.startswith("layer-")] == [f"layer-{layer}"]


def test_output_mode_outline_removes_editable_text(tmp_path):
    spec, prepared, _ = fixture_scene(formats=["svg"], page={"text_mode": "outline"})
    render_scene(compile_scene(prepared, spec, "general"), spec, tmp_path)
    root = ET.parse(tmp_path / "general.svg").getroot()
    assert list(root.iter(f"{SVG}text")) == []
    title = next(e for e in root.iter() if e.attrib.get("id") == "title")
    assert list(title.iter(f"{SVG}use"))


def test_filter_language_rejects_code_and_validates_unreached_branches():
    for bad in ({"eval": "__import__('os')"}, {"all": [{}, {"unknown": []}]},
                {"eq": ["highway", {"x": 1}]}, {"all": []}, {"in": ["highway", "primary"]}):
        with pytest.raises(UmapError, match="filter|Filter|requires|Unsupported"):
            validate_filter(bad)
    spec, prepared, _ = fixture_scene()
    data = spec.model_dump()
    data["style"]["rules"] = [
        {"layer": "roads", "when": {"has": "highway"}, "paint": {"stroke": "#00FF00"}},
        {"layer": "roads", "when": {"all": [{"eq": ["highway", "primary"]},
                                              {"in": ["highway", ["primary", "secondary"]]}]},
         "paint": {"stroke": "#FF0000"}},
    ]
    # Public validation materializes rule models before entering the renderer.
    spec = MapSpec.model_validate(data)
    scene = compile_scene(prepared, spec, "general")
    road = next(p for g in scene.groups for p in g.paths if p.feature_id == "osm/way/2")
    assert road.paint.stroke == "#FF0000"


def test_text_preflight_reports_missing_glyph_and_overflow():
    spec, prepared, _ = fixture_scene()
    spec.title = "Unsupported \U0001FAE0"
    with pytest.raises(UmapError) as error:
        compile_scene(prepared, spec, "general")
    assert error.value.code == "MISSING_GLYPH"
    spec.title = "W" * 180
    with pytest.raises(UmapError) as error:
        compile_scene(prepared, spec, "general")
    assert error.value.code == "TEXT_OVERFLOW"


def test_road_tunnel_base_bridge_and_level_order():
    spec, prepared, _ = fixture_scene()
    road = next(f for f in prepared.features if f.layer == "roads")
    variants = [road.model_copy(update={"id": identifier, "properties": props})
                for identifier, props in [("b", {"bridge": "yes"}), ("c", {}),
                                           ("a", {"tunnel": "yes"}),
                                           ("d", {"layer": "2", "bridge": "yes"})]]
    prepared.features[:] = variants
    scene = compile_scene(prepared, spec, "general")
    roads = next(g for g in scene.groups if g.id == "layer-roads")
    assert [p.feature_id for p in roads.paths] == ["a", "c", "b", "d"]
    assert roads.paths[0].paint.dash_pt


@pytest.mark.parametrize("size,orientation", [("A3", "portrait"), ("A3", "landscape"),
                                             ("A4", "portrait"), ("A4", "landscape")])
def test_both_page_sizes_and_orientations_compile(size, orientation):
    fixture_scene(page={"size": size, "orientation": orientation})


def test_styles_do_not_expose_mutable_global_defaults():
    first = list_styles()
    first[0]["defaults"]["roads"]["stroke"] = "#123456"
    assert list_styles()[0]["defaults"]["roads"]["stroke"] != "#123456"


def test_river_centerline_has_visible_stroke_and_respects_explicit_overrides():
    spec, prepared, _ = fixture_scene()
    road = next(f for f in prepared.features if f.layer == "roads")
    river = road.model_copy(update={"id": "osm/way/river", "layer": "water",
                                    "properties": {"waterway": "river"}})
    prepared.features[:] = [river]

    def river_path(recipe):
        scene = compile_scene(prepared, recipe, "water")
        return next(p for g in scene.groups for p in g.paths if p.feature_id == river.id)

    default = river_path(spec)
    assert default.paint.stroke == "#D4E3E8"
    assert default.paint.fill is None
    assert default.paint.width_pt == pytest.approx(0.2*PT_PER_MM)
    spec.style.layers["water"] = {"fill": "#FF0000"}
    assert river_path(spec).paint.stroke == "#FF0000"
    spec.style.layers["water"] = {"stroke": "#0000FF", "width_mm": 0.4}
    assert river_path(spec).paint.stroke == "#0000FF"
    assert river_path(spec).paint.width_pt == pytest.approx(0.4*PT_PER_MM)


def test_raster_batching_preserves_alpha_holes_clipping_and_road_order(tmp_path):
    import numpy as np

    spec, prepared, _ = fixture_scene(formats=["png"], page={"dpi": 100})
    xmin, ymin, xmax, ymax = prepared.bounds
    cx, cy = (xmin+xmax)/2, (ymin+ymax)/2
    building = next(f for f in prepared.features if f.layer == "buildings")
    prepared.features.append(building.model_copy(update={"id": "overlap",
        "geometry": mapping(box(cx,cy-100,cx+350,cy+300))}))
    prepared.features.extend([
        Feature(id="tunnel", layer="roads", properties={"tunnel": "yes"},
                geometry=mapping(LineString([(xmin-100,cy), (xmax+100,cy)]))),
        Feature(id="bridge", layer="roads", properties={"bridge": "yes"},
                geometry=mapping(LineString([(cx,ymin-100), (cx,ymax+100)]))),
    ])
    data = spec.model_dump()
    data["style"]["layers"]["buildings"] = {"opacity": 0.5}
    data["style"]["rules"] = [
        {"layer": "roads", "when": {"has": "tunnel"}, "paint": {"stroke": "#00FF00", "width_mm": 1}},
        {"layer": "roads", "when": {"has": "bridge"}, "paint": {"stroke": "#FF0000", "width_mm": 1}},
    ]
    spec = MapSpec.model_validate(data)
    scene = compile_scene(prepared, spec, "general")
    images = []
    with rc_context({"path.simplify": False, "lines.scale_dashes": False}):
        for raster in (False, True):
            fig = _figure(scene, raster=raster)
            fig.set_size_inches(round(scene.width_pt/72*100)/100,
                                round(scene.height_pt/72*100)/100)
            path = tmp_path / f"batch-{raster}.png"
            fig.savefig(path, dpi=100)
            images.append(np.asarray(Image.open(path).convert("RGB")))
            fig.clear()
    # Different Agg entry points may round antialiased boundary coverage by one
    # channel value. Interior fills, winding holes, opacity and ordering must agree.
    delta = np.abs(images[0].astype(int)-images[1].astype(int))
    assert delta.max() <= 1
