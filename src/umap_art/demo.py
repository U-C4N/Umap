"""Offline first-use examples shipped with the installed package."""

from __future__ import annotations

from contextlib import ExitStack
from importlib.resources import as_file, files
from pathlib import Path

from .errors import UmapError
from .models import MapSpec, RenderResult, StyleSpec

PRESETS = ("poster", "guide", "atlas", "pocket", "field-cards")


def render_demo(
    preset: str = "poster", *, theme: str | None = None, output_dir: str | Path = "outputs",
    places_csv: str | Path | None = None
) -> RenderResult:
    """Render a bundled recipe without fetching data or changing package resources."""
    if preset not in PRESETS:
        raise ValueError(f"Unknown demo preset: {preset}")
    resources = files("umap_art").joinpath("examples", "kadikoy")
    recipe_name = f"{preset}.json"
    required = (recipe_name, "snapshot.json", "DATA-LICENSES.txt")
    missing = [name for name in required if not resources.joinpath(name).is_file()]
    if missing:
        raise UmapError(
            "DEMO_DATA_MISSING",
            "Bundled demo data is missing; reinstall the complete umap-art package",
            {"missing": missing},
        )

    spec = MapSpec.model_validate_json(
        resources.joinpath(recipe_name).read_text(encoding="utf-8")
    )
    if places_csv is not None:
        from .places import read_places_csv

        spec.places = read_places_csv(places_csv)
    spec = MapSpec.model_validate(spec.model_dump())
    if theme is not None:
        defaults = {} if preset == "field-cards" else spec.style.model_dump()
        spec.style = StyleSpec.model_validate(defaults | {"theme": theme})
    if spec.area.place:
        raise ValueError("Bundled demo recipes must use coordinates, not a place lookup")

    from .service import render

    # Keep extracted resources alive until the shared renderer has copied the
    # verified snapshot into the portable output project.
    with ExitStack() as stack:
        snapshot = stack.enter_context(as_file(resources.joinpath("snapshot.json")))
        spec.source.snapshot = str(snapshot.resolve())
        spec.source.offline = True
        if preset == "field-cards" and places_csv is None:
            for place in spec.places:
                photo = stack.enter_context(as_file(resources.joinpath(place.reference_photo)))
                place.reference_photo = str(photo.resolve())
        return render(spec, output_dir=output_dir)
