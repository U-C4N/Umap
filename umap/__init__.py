"""Umap - A Python library for drawing customized maps from OpenStreetMap data."""
from .core.plot import plot, multiplot, Plot, Subplot
from .core.fetch import get_gdfs
from .utils.drawing import add_frame
from .utils.styles import get_style, list_styles, register_style
from .utils.cache import get_cache, clear_cache, get_cache_info
from .utils.optimization import auto_optimize_layers, check_data_quality, get_processing_stats
from .cli import main as cli_main

# Package version
__version__ = "3.0.0"

__all__ = [
    'plot', 'multiplot', 'Plot', 'Subplot', 'get_gdfs', 'add_frame',
    'get_style', 'list_styles', 'register_style',
    'get_cache', 'clear_cache', 'get_cache_info',
    'auto_optimize_layers', 'check_data_quality', 'get_processing_stats',
    'cli_main'
]
