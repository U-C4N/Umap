"""Sequential, opt-in live geographic smoke checks against keyless providers.

Run with ``python scripts/probe_cities.py`` from the repository root. This is not
part of offline CI: failures and partial service availability are recorded in
the report instead of being labelled as passing geography checks.
"""
from __future__ import annotations

import json
import os
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from umap_art.models import MapSpec
from umap_art.service import load_snapshot, render


def main():
    output = Path("outputs/cities").resolve()
    output.mkdir(parents=True, exist_ok=True)
    os.environ["UMAP_CACHE_DIR"] = str(Path(".cache/umap").resolve())
    report = {"started_at": datetime.now(timezone.utc).isoformat(), "cities": [],
              "visual_review_performed": False,
              "configuration": {"page": "A4 landscape", "scale": 3000, "dpi": 72,
                                "formats": ["png", "svg"], "include_ocean": True}}
    cities = [("Ankara", 32.8541, 39.9208), ("Amsterdam", 4.8952, 52.3702),
              ("Venice", 12.3358, 45.4372), ("Barcelona", 2.1734, 41.3851)]
    for name, lon, lat in cities:
        started = time.perf_counter()
        entry = {"city": name, "center": [lon, lat], "status": "running"}
        print(json.dumps(entry), flush=True)
        try:
            spec = MapSpec(area={"center": [lon, lat], "scale_denominator": 3000},
                           page={"size": "A4", "orientation": "landscape", "dpi": 72},
                           title=name, source={"include_ocean": True},
                           formats=["png", "svg"], bundle=False)
            result = render(spec, output_dir=output / name.lower())
            data, dataset_id = load_snapshot(Path(result.snapshot_path))
            layers = {layer: sum(feature.layer == layer for feature in data.features)
                      for layer in ("buildings", "roads", "green", "water")}
            entry.update(status="succeeded", features=len(data.features), layer_counts=layers,
                         dataset_id=dataset_id, sources=data.sources,
                         feature_id_prefix_counts=dict(Counter(feature.id.split("/")[0] for feature in data.features)),
                         source_summary=[{key: source[key] for key in (
                             "provider", "release", "data_timestamp", "selected_files",
                             "selected_row_groups", "decoded_column_bytes") if key in source}
                             for source in data.sources],
                         diagnostics=[d.model_dump(mode="json") for d in result.diagnostics],
                         result=result.model_dump(mode="json"))
        except Exception as exc:
            entry.update(status="failed", error=exc.to_dict() if hasattr(exc, "to_dict") else {
                "code": type(exc).__name__, "message": str(exc)})
        entry["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        report["cities"].append(entry)
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({key: value for key, value in entry.items()
                          if key not in ("result", "sources", "diagnostics")}, ensure_ascii=False), flush=True)
    return 0 if all(city["status"] == "succeeded" for city in report["cities"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
