"""Umap - A Python library for drawing customized maps from OpenStreetMap data."""
from .core.plot import plot, multiplot, Plot, Subplot
from .core.fetch import get_gdfs
from .utils.drawing import add_frame
from .cli import main as cli_main

# Package version
__version__ = "2.0"

__all__ = ['plot', 'multiplot', 'Plot', 'Subplot', 'get_gdfs', 'add_frame', 'cli_main']
