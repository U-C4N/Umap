"""Export the versioned public JSON Schemas included in source and wheel builds."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from umap_art.models import Dataset, MapSpec, RenderResult, StyleSpec

SCHEMAS = {
    "map-spec.schema.json": MapSpec,
    "style-spec.schema.json": StyleSpec,
    "render-result.schema.json": RenderResult,
    "dataset.schema.json": Dataset,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).resolve().parents[1] / "src" / "umap_art" / "schemas" / "v1")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for filename, model in SCHEMAS.items():
        schema = {"$schema": "https://json-schema.org/draft/2020-12/schema",
                  **model.model_json_schema()}
        (args.output / filename).write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n",
                                           encoding="utf-8")
    print(json.dumps({"output": str(args.output.resolve()), "files": sorted(SCHEMAS)}))


if __name__ == "__main__":
    main()
