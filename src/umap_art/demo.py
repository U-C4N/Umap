"""Offline first-use examples shipped with the installed package."""

from __future__ import annotations

from importlib.resources import as_file, files
from pathlib import Path

from .errors import UmapError
from .models import MapSpec, RenderResult, StyleSpec

PRESETS = ("poster", "guide", "atlas")


def render_demo(
    preset: str = "poster", *, theme: str | None = None, output_dir: str | Path = "outputs"
) -> RenderResult:
    """Render a bundled recipe without fetching data or changing package resources."""
    if preset not in PRESETS:
        raise ValueError(f"Unknown demo preset: {preset}")
    resources = files("umap_art").joinpath("examples", "kadikoy")
    required = (f"{preset}.json", "snapshot.json", "DATA-LICENSES.txt")
    missing = [name for name in required if not resources.joinpath(name).is_file()]
    if missing:
        raise UmapError(
            "DEMO_DATA_MISSING",
            "Bundled demo data is missing; reinstall the complete umap-art package",
            {"missing": missing},
        )

    spec = MapSpec.model_validate_json(
        resources.joinpath(f"{preset}.json").read_text(encoding="utf-8")
    )
    if theme is not None:
        spec.style = StyleSpec.model_validate(spec.style.model_dump() | {"theme": theme})
    if spec.area.place:
        raise ValueError("Bundled demo recipes must use coordinates, not a place lookup")

    from .service import render

    # Keep extracted resources alive until the shared renderer has copied the
    # verified snapshot into the portable output project.
    with as_file(resources.joinpath("snapshot.json")) as snapshot:
        spec.source.snapshot = str(snapshot.resolve())
        spec.source.offline = True
        return render(spec, output_dir=output_dir)
