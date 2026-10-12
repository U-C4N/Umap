from __future__ import annotations

import io

import httpx
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from shapely.geometry import box, shape

from umap_art.errors import UmapError
from umap_art.models import MapSpec
from umap_art.sources import common, overture, photon
from umap_art.sources.common import Budget, request_bytes
from umap_art.sources.overpass import make_query, parse_osm


def xml_path(tmp_path, body):
    path = tmp_path / "source.osm"
    path.write_text(f'<?xml version="1.0"?><osm version="0.6">{body}</osm>', encoding="utf-8")
    return path


def test_osm_assembly_preserves_courtyard_and_road_metadata(tmp_path):
    points = [(0, 0), (1, 0), (1, 1), (0, 1), (.2, .2), (.8, .2), (.8, .8), (.2, .8)]
    nodes = "".join(f'<node id="{i}" lat="{lat}" lon="{lon}"/>' for i, (lon, lat) in enumerate(points, 1))
    ways = '<way id="10">' + "".join(f'<nd ref="{i}"/>' for i in [1, 2, 3, 4, 1]) + '</way>'
    ways += '<way id="11">' + "".join(f'<nd ref="{i}"/>' for i in [5, 6, 7, 8, 5]) + '</way>'
    ways += '<way id="12"><nd ref="1"/><nd ref="2"/><tag k="highway" v="primary"/><tag k="bridge" v="yes"/><tag k="layer" v="1"/></way>'
    relation = '<relation id="100"><member type="way" ref="10" role="outer"/><member type="way" ref="11" role="inner"/><tag k="type" v="multipolygon"/><tag k="building" v="yes"/></relation>'
    dataset = parse_osm(xml_path(tmp_path, nodes + ways + relation), (0, 0, 1, 1))
    building = next(f for f in dataset.features if f.layer == "buildings")
    assert building.id == "osm:relation/100"
    geometry = shape(building.geometry)
    assert len(geometry.geoms[0].interiors) == 1
    assert geometry.area == pytest.approx(.64)
    assert next(f for f in dataset.features if f.layer == "roads").properties["bridge"] == "yes"


def test_osm_empty_is_not_a_provider_failure(tmp_path):
    dataset = parse_osm(xml_path(tmp_path, '<meta osm_base="2026-10-12T00:00:00Z"/>'), (0, 0, 1, 1))
    assert dataset.features == []
    assert dataset.sources[0]["data_timestamp"] == "2026-10-12T00:00:00Z"


@pytest.mark.parametrize("body,code", [
    ('<node id="1" lon="0" lat="0"/><way id="2"><nd ref="1"/><nd ref="3"/><tag k="highway" v="path"/></way>', "source_incomplete"),
    ('<remark>Query timed out</remark>', "source_incomplete"),
    ('<way id="1">', "source_schema"),
    ('<relation id="1"><member type="way" ref="5" role="outer"/></relation>', "source_incomplete"),
    ('<node id="1" lon="nan" lat="0"/>', "source_schema"),
])
def test_osm_partial_and_broken_responses_fail(tmp_path, body, code):
    with pytest.raises(UmapError) as exc:
        parse_osm(xml_path(tmp_path, body), (0, 0, 1, 1))
    assert exc.value.code == code


def test_overpass_query_bbox_order_and_dependency_expansion():
    query = make_query((28, 40, 29, 41))
    assert '(40.000000000,28.000000000,41.000000000,29.000000000)' in query
    assert '>>;' in query
    assert '[out:xml]' in query


def test_xml_declaration_beyond_header_is_rejected(tmp_path):
    path = tmp_path / "entity.osm"
    path.write_text('<?xml version="1.0"?>' + '<!--' + 'x' * 70000 + '-->'
                    + '<!DOCTYPE osm [<!ENTITY bad "text">]><osm version="0.6"/>')
    with pytest.raises(UmapError, match="declarations"):
        parse_osm(path, (0, 0, 1, 1))


def photon_response():
    return {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {
        "type": "Point", "coordinates": [29.027, 40.99]}, "properties": {
        "name": "Kadıköy", "city": "İstanbul", "country": "Türkiye", "countrycode": "TR",
        "osm_type": "R", "osm_id": 123, "extent": [29, 41.1, 29.1, 40.9]}}]}


def test_photon_normalizes_extent_and_caches(tmp_path, monkeypatch):
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json=photon_response())

    monkeypatch.setattr(photon, "new_client", lambda: httpx.Client(transport=httpx.MockTransport(respond)))
    first = photon.find_locations("Kadıköy", cache_dir=tmp_path)
    second = photon.find_locations("Kadıköy", cache_dir=tmp_path)
    assert first == second
    assert first[0]["center"] == [29.027, 40.99]
    assert first[0]["bbox"] == [29, 40.9, 29.1, 41.1]
    assert len(requests) == 1


def test_http_size_budget_and_retry(monkeypatch):
    calls = []
    monkeypatch.setattr(common.time, "sleep", lambda n: None)

    def respond(request):
        calls.append(request)
        return httpx.Response(429 if len(calls) < 2 else 200, content=b"a" * 30)

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        data, _ = request_bytes(client, "GET", "https://example.test/data", Budget(3, 100))
    assert data == b"a" * 30 and len(calls) == 2
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, content=b"x" * 100))) as client:
        with pytest.raises(UmapError, match="byte budget"):
            request_bytes(client, "GET", "https://example.test/data", Budget(3, 20))


def parquet_bytes(rows, row_group_size=None):
    output = io.BytesIO()
    pq.write_table(pa.Table.from_pylist(rows), output, row_group_size=row_group_size)
    return output.getvalue()


def ocean_fixtures():
    # Enclosing ocean's vertices lie outside the query; bbox overlap must retain it.
    ocean = box(-10, -10, 10, 10)
    lake = box(.1, .1, .2, .2)
    far = box(80, 60, 81, 61)
    rows = [{"id": label, "subtype": subtype, "geometry": geometry.wkb,
             "bbox": dict(zip(("xmin", "ymin", "xmax", "ymax"), geometry.bounds))}
            for label, subtype, geometry in [("enclosing", "ocean", ocean), ("lake", "lake", lake), ("far", "ocean", far)]]
    index = parquet_bytes([{"collection": "water", "type": "Feature", "bbox": {
        "xmin": -10., "ymin": -10., "xmax": 81., "ymax": 61.}, "assets": {
        "aws": {"href": "https://example.test/water.parquet"}}}])
    return index, parquet_bytes(rows, 1)


def test_overture_range_reads_prune_rows_and_retain_enclosing_ocean(tmp_path, monkeypatch):
    index, water = ocean_fixtures()
    requests = []

    def respond(request):
        requests.append(request)
        if request.url.path == "/catalog.json":
            return httpx.Response(200, json={"latest": "2026-09-23.1", "links": [
                {"rel": "child", "href": "./2026-09-23.1/catalog.json"}]})
        if request.url.path.endswith("collections.parquet"):
            return httpx.Response(200, content=index)
        assert request.url.path == "/water.parquet"
        assert "range" in request.headers
        first, last = map(int, request.headers["range"].split("=")[1].split("-"))
        return httpx.Response(206, content=water[first:last+1], headers={"Content-Range": f"bytes {first}-{last}/{len(water)}"})

    monkeypatch.setattr(overture, "new_client", lambda: httpx.Client(transport=httpx.MockTransport(respond)))
    spec = MapSpec(area={"center": [.5, .5]}, source={"overture_catalog_url": "https://example.test/catalog.json"})
    dataset = overture.fetch_ocean(spec, (0, 0, 1, 1), tmp_path, Budget())
    assert [f.id for f in dataset.features] == ["overture:enclosing"]
    assert dataset.sources[0]["selected_row_groups"] == 2
    assert dataset.sources[0]["release"] == "2026-09-23.1"
    assert all(record["sha256"] for record in dataset.sources[0]["raw_files"])


def test_overture_missing_catalog_never_falls_back_to_global_scan(tmp_path, monkeypatch):
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(200, json={"latest": "unknown"})

    monkeypatch.setattr(overture, "new_client", lambda: httpx.Client(transport=httpx.MockTransport(respond)))
    with pytest.raises(UmapError) as exc:
        overture.fetch_ocean(MapSpec(area={"center": [0, 0]}), (0, 0, 1, 1), tmp_path, Budget())
    assert exc.value.code == "source_schema"
    assert len(calls) == 1


def test_parquet_server_ignoring_range_is_rejected(tmp_path):
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, content=b"PAR1xxxx"))) as client:
        with pytest.raises(UmapError, match="HTTP ranges"):
            overture.HTTPRangeReader(client, "https://example.test/full.parquet", tmp_path, Budget())


def test_overture_unknown_index_schema_is_error():
    with pytest.raises(UmapError) as exc:
        overture.select_assets(parquet_bytes([{"unexpected": 1}]), (0, 0, 1, 1))
    assert exc.value.code == "source_schema"


@pytest.mark.live
def test_live_keyless_small_kadikoy_dataset(tmp_path):
    from umap_art.sources import acquire, find_locations

    candidates = find_locations("Kadikoy Istanbul", cache_dir=tmp_path)
    assert candidates and all(len(candidate["center"]) == 2 for candidate in candidates)
    spec = MapSpec(area={"bbox": [29.017, 40.987, 29.027, 40.996]})
    dataset = acquire(spec, spec.area.bbox, cache_dir=tmp_path)
    assert {source["provider"] for source in dataset.sources} == {"overpass", "overture"}
    assert {"roads", "buildings"}.issubset({feature.layer for feature in dataset.features})
    assert any(feature.properties.get("subtype") == "ocean" for feature in dataset.features)
