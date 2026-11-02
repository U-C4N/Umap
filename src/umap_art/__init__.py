"""Umap's stable Python API."""

from .models import MapSpec, RenderResult

__version__ = "0.3.0"


def render(spec: MapSpec, *, output_dir="outputs", places_csv=None) -> RenderResult:
    from .service import render as _render

    return _render(spec, output_dir=output_dir, places_csv=places_csv)


__all__ = ["MapSpec", "RenderResult", "render"]
