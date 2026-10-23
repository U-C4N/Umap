"""Public version rejection and distributable schema export acceptance tests."""
from __future__ import annotations

import json
import subprocess
import sys
from importlib.resources import files
from pathlib import Path

import pytest
from pydantic import ValidationError

from umap_art.models import RenderResult, StyleSpec


@pytest.mark.parametrize("model,payload", [
    (StyleSpec, {"theme": "architectural"}),
    (RenderResult, {"artifacts": [], "manifest_path": "manifest.json",
                    "recipe_path": "recipe.json", "snapshot_path": "snapshot.json",
                    "dataset_id": "test", "scene_hashes": {}}),
])
def test_standalone_documents_default_to_v1_and_reject_unknown_versions(model, payload):
    assert model.model_validate(payload).model_dump()["schema_version"] == "1"
    with pytest.raises(ValidationError) as error:
        model.model_validate({**payload, "schema_version": "2"})
    assert any(e["loc"] == ("schema_version",) and e["type"] == "literal_error"
               for e in error.value.errors())


def test_schema_export_cli_and_packaged_resources(tmp_path):
    script = Path(__file__).resolve().parents[1] / "scripts" / "export_schemas.py"
    destination = tmp_path / "exported"
    result = subprocess.run([sys.executable, str(script), "--output", str(destination)],
                            capture_output=True, text=True, encoding="utf-8", check=True)
    exported = json.loads(result.stdout)
    assert set(exported["files"]) == {"map-spec.schema.json", "style-spec.schema.json",
                                      "render-result.schema.json", "dataset.schema.json"}
    packaged = files("umap_art").joinpath("schemas", "v1")
    for name in exported["files"]:
        assert json.loads((destination/name).read_text(encoding="utf-8")) == json.loads(
            packaged.joinpath(name).read_text(encoding="utf-8"))
        for contents in [(destination/name).read_text(encoding="utf-8"),
                         packaged.joinpath(name).read_text(encoding="utf-8")]:
            schema = json.loads(contents)
            assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
            assert schema["type"] == "object"
            assert schema["properties"]["schema_version"]["const"] == "1"
            assert schema["additionalProperties"] is False
