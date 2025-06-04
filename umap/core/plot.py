"""Core plotting functionality."""
import os
import json
import pathlib
import warnings
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Dict, Optional, Union, Tuple, List, Any
import matplotlib.figure
import matplotlib.axes
import geopandas as gp
import shapely.ops
import shapely.affinity
from copy import deepcopy
from matplotlib.patches import PathPatch
from matplotlib.path import Path
from shapely.geometry import (
    Point,
    LineString,
    MultiLineString,
    Polygon,
    MultiPolygon,
    GeometryCollection,
    box,
)
from shapely.geometry.base import BaseGeometry
from .fetch import get_gdfs
from ..utils.cache import get_cache
from ..utils.optimization import optimize_layer_config

try:
    import vsketch
except ImportError:
    warnings.warn(
        'Install vsketch with "pip install git+https://github.com/abey79/vsketch@1.0.0" to enable pen plotter mode.'
    )

@dataclass
class Plot:
    """Plot object containing geodataframes and matplotlib objects."""
    geodataframes: Dict[str, gp.GeoDataFrame]
    fig: Optional[matplotlib.figure.Figure]
    ax: Optional[matplotlib.axes.Axes]
    background: Optional[BaseGeometry]

class Subplot:
    """Class for organizing multiple map views."""
    def __init__(self, query, **kwargs):
        self.query = query
        self.kwargs = kwargs

def transform_gdfs(
    gdfs: Dict[str, gp.GeoDataFrame],
    x: float = 0,
    y: float = 0,
    scale_x: float = 1,
    scale_y: float = 1,
    rotation: float = 0,
) -> Dict[str, gp.GeoDataFrame]:
    """Apply geometric transformations to GeoDataFrames."""
    collection = GeometryCollection(
        [GeometryCollection(list(gdf.geometry)) for gdf in gdfs.values()]
    )
    collection = shapely.affinity.translate(collection, x, y)
    collection = shapely.affinity.scale(collection, scale_x, scale_y)
    collection = shapely.affinity.rotate(collection, rotation)
    
    for i, layer in enumerate(gdfs):
        gdfs[layer].geometry = list(collection.geoms[i].geoms)
    
    return gdfs

def PolygonPatch(shape: BaseGeometry, **kwargs) -> PathPatch:
    """Create matplotlib PathPatch from shapely geometry."""
    vertices, codes = [], []
    for geom in shape.geoms if hasattr(shape, "geoms") else [shape]:
        for poly in geom.geoms if hasattr(geom, "geoms") else [geom]:
            if type(poly) != Polygon:
                continue
            exterior = np.array(poly.exterior.xy)
            interiors = [np.array(interior.xy) for interior in poly.interiors]
            vertices += [exterior] + interiors
            codes += list(
                map(
                    lambda p: [Path.MOVETO] + [Path.LINETO] * (p.shape[1] - 2) + [Path.CLOSEPOLY],
                    [exterior] + interiors,
                )
            )
    return PathPatch(
        Path(np.concatenate(vertices, 1).T, np.concatenate(codes)), **kwargs
    )

def plot_gdf(
    layer: str,
    gdf: gp.GeoDataFrame,
    ax: Optional[matplotlib.axes.Axes],
    mode: str = "matplotlib",
    vsk=None,
    palette: Optional[List[str]] = None,
    width: Optional[Union[dict, float]] = None,
    **kwargs,
) -> None:
    """Plot a GeoDataFrame layer."""
    if mode == "matplotlib" and ax is not None:
        for shape in gdf.geometry:
            if isinstance(shape, (Polygon, MultiPolygon)):
                # Get fill color from palette if provided
                fc = kwargs.get('fc')
                if palette and not fc:
                    fc = np.random.choice(palette)
                
                # Get hatch color, defaulting to edge color
                hatch_c = kwargs.get('hatch_c', kwargs.get('ec', '#2F3737'))
                
                # Create main patch with fill and hatching
                ax.add_patch(
                    PolygonPatch(
                        shape,
                        lw=0,  # No edge for main patch
                        ec=hatch_c,  # Use hatch color for pattern
                        fc=fc if fc else '#fff',
                        hatch=kwargs.get('hatch', None),
                        **{k: v for k, v in kwargs.items() if k not in ['lw', 'ec', 'fc', 'hatch', 'hatch_c', 'palette']},
                    )
                )
                
                # Create outline patch
                ax.add_patch(
                    PolygonPatch(
                        shape,
                        fc='none',  # Transparent fill
                        ec=kwargs.get('ec', '#2F3737'),
                        lw=kwargs.get('lw', 0),
                        **{k: v for k, v in kwargs.items() if k not in ['fc', 'ec', 'lw', 'hatch', 'hatch_c', 'palette']},
                    )
                )
            elif isinstance(shape, (LineString, MultiLineString)):
                if isinstance(shape, LineString):
                    if ax is not None:
                        ax.plot(
                            *shape.xy,
                            c=kwargs.get('ec', '#2F3737'),
                            linewidth=kwargs.get('lw', 0.5),
                            alpha=kwargs.get('alpha', 1),
                            **{k: v for k, v in kwargs.items() if k in ["ls", "dashes", "zorder"]},
                        )
                else:
                    for line in shape.geoms:
                        if ax is not None:
                            ax.plot(
                                *line.xy,
                                c=kwargs.get('ec', '#2F3737'),
                                linewidth=kwargs.get('lw', 0.5),
                                alpha=kwargs.get('alpha', 1),
                                **{k: v for k, v in kwargs.items() if k in ["ls", "dashes", "zorder"]},
                            )
    elif mode == "plotter" and vsk:
        if kwargs.get("draw", True):
            vsk.stroke(kwargs.get("stroke", 1))
            vsk.penWidth(kwargs.get("penWidth", 0.3))
            if "fill" in kwargs:
                vsk.fill(kwargs["fill"])
            else:
                vsk.noFill()
            for shape in gdf.geometry:
                vsk.geometry(shape)
    else:
        raise ValueError(f"Unknown mode {mode}")

def create_background(
    gdfs: Dict[str, gp.GeoDataFrame],
    style: Dict[str, dict]
) -> Tuple[BaseGeometry, float, float, float, float, float, float]:
    """Create background layer and get bounds."""
    background_pad = style.get("background", {}).get("pad", 1.1)
    background = shapely.affinity.scale(
        box(*shapely.ops.unary_union(gdfs["perimeter"].geometry).bounds),
        background_pad,
        background_pad,
    )
    
    if "background" in style and "dilate" in style["background"]:
        background = background.buffer(style["background"].pop("dilate"))
    
    xmin, ymin, xmax, ymax = background.bounds
    dx, dy = xmax - xmin, ymax - ymin
    
    return background, xmin, ymin, xmax, ymax, dx, dy

def plot(
    query: Union[str, Tuple[float, float], gp.GeoDataFrame],
    layers: Optional[Dict] = None,
    style: Optional[Dict] = None,
    preset: str = "default",
    circle: Optional[bool] = None,
    radius: Optional[float] = None,
    dilate: Optional[float] = None,
    figsize: Tuple[int, int] = (12, 12),
    mode: str = "matplotlib",
    use_cache: bool = True,
    auto_optimize: bool = True,
    **kwargs
) -> Plot:
    """Draw a map from OpenStreetMap data.

    Args:
        use_cache: Enable reading/writing from the local cache.
        auto_optimize: Optimize layer configuration based on ``radius``.
    """
    # Default minimalist style if no style provided
    if style is None:
        style = {
            'perimeter': {'fill': False, 'lw': 0, 'zorder': 0},
            'background': {'fc': '#fff', 'zorder': -1},
            'streets': {'ec': '#000', 'lw': 0.5, 'zorder': 4},
            'building': {'ec': '#000', 'fc': '#fff', 'lw': 0.5, 'zorder': 5}
        }
    
    # Default layers if none provided
    layers = layers or {
        'perimeter': {},
        'streets': {
            'width': {
                'primary': 4,
                'secondary': 3,
                'tertiary': 2,
                'residential': 2
            }
        },
        'building': {'tags': {'building': True}}
    }

    fetch_layers = deepcopy(layers)
    if auto_optimize and radius is not None:
        fetch_layers = optimize_layer_config(fetch_layers, radius)

    cache = get_cache() if use_cache else None
    if cache:
        cached = cache.get_cached_data(query, radius, fetch_layers)
        if cached is not None:
            gdfs = cached
        else:
            gdfs = get_gdfs(query, fetch_layers, radius, dilate)
            cache.cache_data(query, radius, fetch_layers, gdfs)
    else:
        gdfs = get_gdfs(query, fetch_layers, radius, dilate)

    # Initialize matplotlib figure and axis

    if mode == "matplotlib":
        fig = plt.figure(figsize=figsize, dpi=300)
        ax = plt.subplot(111, aspect="equal")
    else:
        # For plotter mode, we don't need matplotlib objects
        return Plot(gdfs, None, None, None)
    
    # Create background
    background, *_ = create_background(gdfs, style)
    
    # Draw layers
    if mode == "matplotlib":
        for layer, gdf in gdfs.items():
            if layer in layers or layer in style:
                plot_gdf(
                    layer,
                    gdf,
                    ax,
                    width=layers.get(layer, {}).get("width"),
                    **(style.get(layer, {})),
                )
        
        # Draw background
        if "background" in style:
            zorder = style["background"].pop("zorder", -1)
            ax.add_patch(
                PolygonPatch(
                    background,
                    **{k: v for k, v in style["background"].items() if k != "dilate"},
                    zorder=zorder,
                )
            )
        
        # Adjust figure
        ax.axis("off")
        ax.axis("equal")
        ax.autoscale()
        plt.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=0, hspace=0)
    
    return Plot(gdfs, fig, ax, background)

def multiplot(*subplots, figsize=(12, 12), **kwargs):
    """Draw multiple maps on the same canvas."""
    fig = plt.figure(figsize=figsize)
    ax = plt.subplot(111, aspect="equal")
    
    mode = "plotter" if kwargs.get("plotter") else "matplotlib"
    
    plots = [
        plot(
            subplot.query,
            ax=ax,
            mode=mode,
            **{**subplot.kwargs, **kwargs}
        )
        for subplot in subplots
    ]
    
    if mode == "matplotlib":
        ax.axis("off")
        ax.axis("equal")
        ax.autoscale()
    
    return plots
