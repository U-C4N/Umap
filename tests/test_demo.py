"""The installed demo is a portable, network-free first project."""

from __future__ import annotations

import json
import shutil
import socket
from contextlib import contextmanager
from importlib.resources import files
from pathlib import Path

import pytest
from PIL import Image

from umap_art import demo
from umap_art.cli import main, parser
from umap_art.errors import UmapError
from umap_art.models import MapSpec, RenderResult
from umap_art.service import render
from umap_art.storage import file_hash
from umap_art.styles import THEMES


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("The packaged demo attempted to access the network")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)


def packaged_data():
    return files("umap_art").joinpath("examples", "kadikoy")


@pytest.fixture
def copied_package(tmp_path, monkeypatch):
    package = tmp_path / "package"
    target = package / "examples" / "kadikoy"
    target.mkdir(parents=True)
    for resource in packaged_data().iterdir():
        if resource.is_file():
            (target / resource.name).write_bytes(resource.read_bytes())
    monkeypatch.setattr(demo, "files", lambda name: package)
    return target


@pytest.mark.parametrize(
    ("preset", "theme", "layout", "views", "place_count"),
    [
        ("poster", "vintage", "poster", ["general"], 3),
        ("guide", "blueprint", "guide", ["general"], 3),
        ("atlas", "architectural", "classic", ["figure_ground", "roads", "green", "water"], 0),
    ],
)
def test_presets_render_offline_and_relocate(
    preset, theme, layout, views, place_count, tmp_path, monkeypatch
):
    package_before = {
        resource.name: resource.read_bytes()
        for resource in packaged_data().iterdir()
        if resource.is_file()
    }
    assert not (tmp_path / "cache").exists()
    monkeypatch.chdir(tmp_path)
    first = demo.render_demo(preset, output_dir="outputs")
    recipe = Path(first.recipe_path)
    spec = MapSpec.model_validate_json(recipe.read_text(encoding="utf-8"))
    assert spec.style.theme == theme
    assert spec.page.layout == layout
    assert spec.page.size == "A4" and spec.page.orientation == "portrait"
    assert spec.page.dpi == 300 and spec.area.scale_denominator == 5000
    assert spec.views == views and len(spec.places) == place_count
    assert spec.source.offline and spec.source.snapshot == "snapshot.json"
    assert spec.bundle
    assert set(spec.formats) == {"png", "svg", "pdf"}
    assert set(first.scene_hashes) == set(views)
    for artifact in first.artifacts:
        path = Path(artifact.path)
        assert path.is_absolute() and path.is_file()
        assert file_hash(path) == artifact.sha256
    for view in views:
        for extension in ("png", "svg", "pdf"):
            assert (recipe.parent / f"{view}.{extension}").is_file()
        with Image.open(recipe.parent / f"{view}.png") as png:
            assert png.size == (round(210 / 25.4 * 300), round(297 / 25.4 * 300))
    assert (recipe.parent / "project.zip").is_file()

    portable = tmp_path / "Taşınmış proje"
    shutil.copytree(recipe.parent, portable)
    # A stale absolute reference to the first export must not rescue this render.
    Path(first.snapshot_path).unlink()
    again = render(portable / "recipe.json", output_dir=tmp_path / "repeated")
    assert again.dataset_id == first.dataset_id
    assert again.scene_hashes == first.scene_hashes
    assert Path(again.recipe_path).parent != recipe.parent
    assert package_before == {
        resource.name: resource.read_bytes()
        for resource in packaged_data().iterdir()
        if resource.is_file()
    }


def test_cli_theme_override_preserves_data_and_previous_exports(tmp_path, capsys):
    first = demo.render_demo(output_dir=tmp_path / "outputs")
    hashes = {artifact.path: file_hash(Path(artifact.path)) for artifact in first.artifacts}
    assert main(["demo", "--preset", "poster", "--theme", "neon", "--output",
                 str(tmp_path / "outputs"), "--json"]) == 0
    second = RenderResult.model_validate_json(capsys.readouterr().out)
    assert first.dataset_id == second.dataset_id
    assert first.scene_hashes != second.scene_hashes
    assert first.recipe_path != second.recipe_path
    assert hashes == {path: file_hash(Path(path)) for path in hashes}
    spec = MapSpec.model_validate_json(Path(second.recipe_path).read_text(encoding="utf-8"))
    assert spec.style.theme == "neon"


@pytest.mark.parametrize("theme", THEMES)
def test_cli_accepts_every_current_theme(theme):
    args = parser().parse_args(["demo", "--theme", theme])
    assert args.theme == theme
    assert args.preset == "poster" and args.output == Path("outputs")


@pytest.mark.parametrize("filename", ["poster.json", "snapshot.json", "DATA-LICENSES.txt"])
def test_missing_packaged_file_has_explicit_error(copied_package, filename, tmp_path):
    (copied_package / filename).unlink()
    with pytest.raises(UmapError) as exc:
        demo.render_demo(output_dir=tmp_path / "output")
    assert exc.value.code == "DEMO_DATA_MISSING"
    assert exc.value.details["missing"] == [filename]
    assert not (tmp_path / "output").exists()


def test_corrupt_snapshot_uses_shared_integrity_error(copied_package, tmp_path):
    snapshot = copied_package / "snapshot.json"
    value = json.loads(snapshot.read_text(encoding="utf-8"))
    value["dataset"]["features"][0]["id"] = "altered-demo-feature"
    snapshot.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(UmapError) as exc:
        demo.render_demo(output_dir=tmp_path / "output")
    assert exc.value.code == "SNAPSHOT_INTEGRITY"
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize("corruption", ["root_list", "null_style", "list_style", "invalid_json"])
def test_corrupt_recipe_with_theme_reports_invalid_input(
    copied_package, corruption, tmp_path, capsys
):
    recipe = copied_package / "poster.json"
    value = json.loads(recipe.read_text(encoding="utf-8"))
    if corruption == "root_list":
        value = []
    elif corruption == "null_style":
        value["style"] = None
    elif corruption == "list_style":
        value["style"] = []
    recipe.write_text(
        "{" if corruption == "invalid_json" else json.dumps(value), encoding="utf-8"
    )
    output = tmp_path / "output"
    assert main(["demo", "--theme", "neon", "--output", str(output), "--json"]) == 2
    streams = capsys.readouterr()
    assert streams.out == ""
    error = json.loads(streams.err.splitlines()[-1])["error"]
    assert error["code"] == "INVALID_INPUT"
    assert "Traceback" not in streams.err
    assert not output.exists()


def test_theme_override_is_validated_before_render(tmp_path):
    with pytest.raises(ValueError, match="theme"):
        demo.render_demo(theme="missing", output_dir=tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_demo_rejects_place_lookup_even_in_a_modified_recipe(copied_package, tmp_path):
    recipe = copied_package / "poster.json"
    value = json.loads(recipe.read_text(encoding="utf-8"))
    value["area"] = {"place": "Kadıköy, İstanbul"}
    recipe.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="place lookup"):
        demo.render_demo(output_dir=tmp_path / "output")


def test_extracted_resource_remains_available_until_render_finishes(tmp_path, monkeypatch):
    import umap_art.service as service

    extracted = tmp_path / "extracted.json"
    sentinel = object()

    @contextmanager
    def extract(resource):
        extracted.write_bytes(resource.read_bytes())
        try:
            yield extracted
        finally:
            extracted.unlink()

    def inspect_resource(spec, *, output_dir):
        assert spec.source.offline
        assert Path(spec.source.snapshot) == extracted.resolve()
        assert extracted.is_file()
        return sentinel

    monkeypatch.setattr(demo, "as_file", extract)
    monkeypatch.setattr(service, "render", inspect_resource)
    assert demo.render_demo(output_dir=tmp_path / "output") is sentinel
    assert not extracted.exists()


@pytest.mark.parametrize("flags", [["--preset", "missing"], ["--theme", "missing"], ["--scale", "500"]])
def test_invalid_demo_flags_fail_before_render(flags, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["demo", *flags])
    assert exc.value.code == 2
    assert capsys.readouterr().out == ""


@pytest.fixture
def reported_result(tmp_path, monkeypatch):
    result = RenderResult(
        artifacts=[
            {"path": str(tmp_path / f"general.{extension}"), "mime_type": mime,
             "sha256": "0" * 64, "size_bytes": 1, "view": "general"}
            for extension, mime in [("png", "image/png"), ("svg", "image/svg+xml"),
                                    ("pdf", "application/pdf")]
        ],
        recipe_path=str(tmp_path / "recipe.json"),
        snapshot_path=str(tmp_path / "snapshot.json"),
        manifest_path=str(tmp_path / "manifest.json"),
        dataset_id="fixture",
        scene_hashes={"general": "scene"},
        diagnostics=[{"code": "EXAMPLE_WARNING", "message": "Visible in stderr"}],
    )
    monkeypatch.setattr(demo, "render_demo", lambda *args, **kwargs: result)
    return result


def test_cli_json_keeps_render_result_schema_and_reports_diagnostics(reported_result, capsys):
    assert main(["demo", "--json"]) == 0
    streams = capsys.readouterr()
    assert json.loads(streams.out) == reported_result.model_dump(mode="json")
    assert "EXAMPLE_WARNING: Visible in stderr" in streams.err
    assert "offline" in streams.err


def test_cli_plain_output_identifies_preview_and_recipe(reported_result, capsys):
    assert main(["demo"]) == 0
    streams = capsys.readouterr()
    assert f"Preview: {reported_result.artifacts[0].path}" in streams.out
    assert f"Recipe: {reported_result.recipe_path}" in streams.out
    assert f"SVG: {reported_result.artifacts[1].path}" in streams.out
    assert f"PDF: {reported_result.artifacts[2].path}" in streams.out
    assert "EXAMPLE_WARNING" not in streams.out
    assert "EXAMPLE_WARNING: Visible in stderr" in streams.err


def test_output_directory_error_is_reported_without_traceback(tmp_path, capsys):
    output = tmp_path / "not-a-directory"
    output.write_text("keep me", encoding="utf-8")
    assert main(["demo", "--output", str(output), "--json"]) == 2
    streams = capsys.readouterr()
    assert streams.out == "" and "INVALID_INPUT" in streams.err
    assert "Traceback" not in streams.err
    assert output.read_text(encoding="utf-8") == "keep me"
