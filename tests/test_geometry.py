import pytest
from shapely.geometry import LineString, Polygon, mapping, shape

from umap_art.errors import UmapError
from umap_art.geometry import Extent, compute_extent, prepare_geometry
from umap_art.models import Dataset, Feature, MapSpec


def test_scale_and_paper_modes():
    a3 = MapSpec(area={"center": [29.025, 40.985], "scale_denominator": 5000})
    first = compute_extent(a3)
    second = compute_extent(
        a3.model_copy(update={"page": a3.page.model_copy(update={"size": "A4"})})
    )
    assert first.scale_denominator == second.scale_denominator == 5000
    assert first.bounds[2] - first.bounds[0] == pytest.approx(2000)
    assert second.bounds[2] - second.bounds[0] < 2000
    fitted = MapSpec(area={"bbox": first.bbox})
    small = fitted.model_copy(update={"page": fitted.page.model_copy(update={"size": "A4"})})
    assert compute_extent(small).scale_denominator > compute_extent(fitted).scale_denominator


def test_large_extent_rejected():
    with pytest.raises(UmapError, match="smaller") as exc:
        compute_extent(MapSpec(area={"center": [29, 41], "scale_denominator": 100000}))
    assert exc.value.code == "AREA_LIMIT"


def test_holes_survive_projection_and_clipping():
    spec = MapSpec(area={"center": [29.025, 40.985]})
    extent = compute_extent(spec)
    polygon = Polygon(
        [(29.024, 40.984), (29.026, 40.984), (29.026, 40.986), (29.024, 40.986)],
        holes=[[(29.0245, 40.9845), (29.0255, 40.9845), (29.0255, 40.9855), (29.0245, 40.9855)]],
    )
    data = Dataset(
        bbox=extent.bbox, features=[Feature(id="b1", layer="buildings", geometry=mapping(polygon))]
    )
    result = prepare_geometry(data, spec, extent)
    assert len(shape(result.features[0].geometry).interiors) == 1


def test_invalid_polygon_requires_explicit_repair():
    spec = MapSpec(area={"center": [29.025, 40.985]})
    extent = compute_extent(spec)
    data = Dataset(
        bbox=extent.bbox,
        features=[
            Feature(
                id="bad",
                layer="buildings",
                geometry=mapping(
                    Polygon(
                        [(29.024, 40.984), (29.026, 40.986), (29.026, 40.984), (29.024, 40.986)]
                    )
                ),
            )
        ],
    )
    with pytest.raises(UmapError) as exc:
        prepare_geometry(data, spec, extent)
    assert exc.value.code == "INVALID_GEOMETRY"
    repaired = prepare_geometry(data, spec.model_copy(update={"geometry_policy": "repair"}), extent)
    assert any(d.code == "GEOMETRY_REPAIRED" for d in repaired.diagnostics)
    assert all(shape(f.geometry).is_valid for f in repaired.features)


def test_overlapping_ocean_is_unioned():
    spec = MapSpec(area={"center": [29.025, 40.985]})
    extent = compute_extent(spec)
    p = Polygon([(29.02, 40.98), (29.03, 40.98), (29.03, 40.99), (29.02, 40.99)])
    data = Dataset(
        bbox=extent.bbox,
        features=[
            Feature(id=f"o{i}", layer="water", geometry=mapping(p), properties={"subtype": "ocean"})
            for i in range(2)
        ],
    )
    result = prepare_geometry(data, spec, extent)
    assert len(result.features) == 1
    assert result.features[0].properties["source_ids"] == ["o0", "o1"]


def test_waterway_clip_retains_line_when_corner_touch_produces_collection():
    spec = MapSpec(area={"center": [5, 5]})
    extent = Extent("EPSG:4326", (0, 0, 10, 10), (0, 0, 10, 10), 5000, 0)
    line = LineString([(1, 1), (11, 1), (11, 11), (10, 10), (11, 9)])
    data = Dataset(
        bbox=extent.bbox, features=[Feature(id="river", layer="water", geometry=mapping(line))]
    )
    result = prepare_geometry(data, spec, extent)
    assert len(result.features) == 1
    assert shape(result.features[0].geometry).equals(LineString([(1, 1), (10, 1)]))
    assert any(d.code == "GEOMETRY_COMPONENT_REMOVED" for d in result.diagnostics)
