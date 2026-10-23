"""Showcase evidence must detect geometry drift and unsafe portable projects."""

from __future__ import annotations

import copy
import importlib.util
import zipfile
from pathlib import Path

import pytest

from umap_art.scene import stable_id

MODULE = importlib.util.spec_from_file_location(
    "release_showcase", Path(__file__).resolve().parents[1] / "scripts/release_showcase.py"
)
showcase = importlib.util.module_from_spec(MODULE)
MODULE.loader.exec_module(showcase)


def test_revision_evidence_rejects_geometry_drift():
    before = {"page": "A4", "geometry_hash": "same", "markers": {"p": "same"},
              "text": {"title": "Before"}}
    after = copy.deepcopy(before)
    after["text"] = {"title": "After", stable_id("b", "place-number"): "1",
                     stable_id("a", "place-number"): "2"}
    first = {"dataset_id": "same", "bounds": [1, 2, 3, 4], "scale_denominator": 5000,
             "style": {"theme": "vintage"}, "places": [{"id": "a"}, {"id": "b"}]}
    second = {**first, "style": {"theme": "neon"}, "places": list(reversed(first["places"]))}
    assert all(showcase.revision_checks(before, after, first, second).values())
    after["geometry_hash"] = "drifted"
    with pytest.raises(ValueError, match="same_map_geometry.*False"):
        showcase.revision_checks(before, after, first, second)


@pytest.mark.parametrize("name", ["../outside.txt", "C:/outside.txt", "/outside.txt"])
def test_portable_archive_cannot_escape_output(tmp_path, name):
    archive = tmp_path / "project.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr(name, "bad")
    with pytest.raises(ValueError, match="Unsafe"):
        showcase.extract_project(archive, tmp_path / "input")
    assert not (tmp_path / "outside.txt").exists()


def test_svg_evidence_requires_editable_vector_structure(tmp_path):
    path = tmp_path / "map.svg"
    path.write_text('<svg xmlns="http://www.w3.org/2000/svg"><image href="x"/></svg>')
    with pytest.raises(ValueError, match="raster"):
        showcase.svg_contract(path)
    path.write_text('<svg xmlns="http://www.w3.org/2000/svg"><g id="x"/><g id="x"/></svg>')
    with pytest.raises(ValueError, match="Duplicate"):
        showcase.svg_contract(path)
