"""Umap's stable Python API."""

from .models import MapSpec, RenderResult

__version__ = "0.2.0"


def render(spec: MapSpec, *, output_dir="outputs") -> RenderResult:
    from .service import render as _render

    return _render(spec, output_dir=output_dir)


__all__ = ["MapSpec", "RenderResult", "render"]
