"""Sanitize an existing, verified snapshot for the bundled Kadikoy example.

No requests are made. Geography and source provenance are retained; local file
locations are removed and the content hash is recomputed. Run only when deliberately
replacing the release's example dataset, then review and rerun its acceptance tests.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path
from typing import Any

from umap_art.models import Dataset, SourceSpec
from umap_art.storage import atomic_json, digest


def is_local_path(value: Any) -> bool:
    """Recognize absolute host paths without mistaking source URLs for paths."""
    return isinstance(value, str) and bool(
        re.match(r"^[A-Za-z]:[\\/]", value)
        or value.startswith(("/", "\\\\", "file://", "~/", "~\\"))
    )


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sanitize(item) for key, item in value.items() if not is_local_path(item)}
    if isinstance(value, list):
        return [_sanitize(item) for item in value if not is_local_path(item)]
    return value


def sanitize_snapshot(envelope: dict) -> dict:
    """Validate the source, strip machine paths, and preserve its geographic content."""
    if envelope.get("schema_version") != "1":
        raise ValueError("Only snapshot schema 1 is supported")
    original = Dataset.model_validate(envelope["dataset"]).model_dump(mode="json")
    if envelope.get("dataset_id") != digest(original):
        raise ValueError("Input snapshot hash does not match its contents")
    clean = _sanitize(copy.deepcopy(envelope))
    dataset = Dataset.model_validate(clean["dataset"]).model_dump(mode="json")
    if dataset["features"] != original["features"] or dataset["bbox"] != original["bbox"]:
        raise ValueError("Sanitization would change geography; review the input manually")
    clean["dataset"] = dataset
    clean["dataset_id"] = digest(dataset)
    if "source_profile" not in clean:
        defaults = SourceSpec()
        profile = {
            "include_ocean": any(s.get("provider") == "overture" for s in dataset["sources"]),
            "overpass_url": defaults.overpass_url,
            "overture_catalog_url": defaults.overture_catalog_url,
        }
        for source in dataset["sources"]:
            key = {"overpass": "overpass_url", "overture": "overture_catalog_url"}.get(
                source.get("provider")
            )
            if key and source.get("endpoint"):
                profile[key] = source["endpoint"]
        clean["source_profile"] = profile
    return clean


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="Existing verified acquisition snapshot")
    parser.add_argument(
        "--output", type=Path,
        default=Path(__file__).resolve().parents[1] / "src/umap_art/examples/kadikoy/snapshot.json",
    )
    args = parser.parse_args()
    if args.snapshot.resolve() == args.output.resolve():
        parser.error("The original acquisition must not be overwritten")
    clean = sanitize_snapshot(json.loads(args.snapshot.read_text(encoding="utf-8")))
    atomic_json(args.output, clean)
    print(json.dumps({"snapshot": str(args.output), "dataset_id": clean["dataset_id"],
                      "features": len(clean["dataset"]["features"])}))


if __name__ == "__main__":
    main()
