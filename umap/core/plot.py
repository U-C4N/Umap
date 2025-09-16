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
from matplotlib.collections import PatchCollection, LineCollection
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
from ..utils.styles import get_style

try:
    import vsketch
except ImportError:
    # vsketch is optional for pen plotter mode
    pass

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
        polygon_main = []
        polygon_outline = []
        polygon_colors = []

        # Polygons
        for shape in gdf.geometry:
            if isinstance(shape, (Polygon, MultiPolygon)):
                fc = kwargs.get('fc')
                if palette and not fc:
                    fc = np.random.choice(palette)
                polygon_colors.append(fc if fc else '#fff')
                polygon_main.append(PolygonPatch(shape))
                polygon_outline.append(PolygonPatch(shape))

        if polygon_main:
            hatch_c = kwargs.get('hatch_c', kwargs.get('ec', '#2F3737'))
            main_collection = PatchCollection(
                polygon_main,
                facecolors=polygon_colors,
                edgecolors=hatch_c,
                linewidths=0,
                hatch=kwargs.get('hatch', None),
                **{k: v for k, v in kwargs.items() if k not in ['lw', 'ec', 'fc', 'hatch', 'hatch_c', 'palette', 'fill']},
            )
            ax.add_collection(main_collection)
            outline_collection = PatchCollection(
                polygon_outline,
                facecolors='none',
                edgecolors=kwargs.get('ec', '#2F3737'),
                linewidths=kwargs.get('lw', 0),
                **{k: v for k, v in kwargs.items() if k not in ['fc', 'ec', 'lw', 'hatch', 'hatch_c', 'palette', 'fill']},
            )
            ax.add_collection(outline_collection)

        # Lines with optional width mapping and casing (mainly for streets)
        if any(isinstance(geom, (LineString, MultiLineString)) for geom in gdf.geometry):
            groups: Dict[float, List[np.ndarray]] = {}

            def get_width_for_row(row) -> float:
                if isinstance(width, dict) and layer == 'streets':
                    highway = getattr(row, 'highway', None)
                    if isinstance(highway, list) and highway:
                        highway = highway[0]
                    if isinstance(highway, str) and highway in width:
                        return float(width[highway])
                    return float(kwargs.get('lw', 0.6))
                elif isinstance(width, (int, float)):
                    return float(width)
                return float(kwargs.get('lw', 0.6))

            for row in gdf.itertuples(index=False):
                geom = row.geometry
                current_width = get_width_for_row(row)
                if isinstance(geom, LineString):
                    groups.setdefault(current_width, []).append(np.column_stack(geom.xy))
                elif isinstance(geom, MultiLineString):
                    for line in geom.geoms:
                        groups.setdefault(current_width, []).append(np.column_stack(line.xy))

            # Draw casing first if requested
            if 'casing_ec' in kwargs and 'casing_scale' in kwargs:
                for lw_value, geoms in groups.items():
                    casing = LineCollection(
                        geoms,
                        colors=kwargs.get('casing_ec'),
                        linewidths=lw_value * float(kwargs.get('casing_scale', 2.0)),
                        alpha=float(kwargs.get('casing_alpha', 1.0)),
                        zorder=max(kwargs.get('zorder', 3) - 0.1, 0),
                    )
                    ax.add_collection(casing)

            # Main stroke
            for lw_value, geoms in groups.items():
                line_collection = LineCollection(
                    geoms,
                    colors=kwargs.get('ec', '#2F3737'),
                    linewidths=lw_value,
                    alpha=kwargs.get('alpha', 1),
                    zorder=kwargs.get('zorder'),
                )
                if 'ls' in kwargs:
                    line_collection.set_linestyle(kwargs['ls'])
                if 'dashes' in kwargs:
                    line_collection.set_dashes(kwargs['dashes'])
                ax.add_collection(line_collection)
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
    background_style = style.get("background", {})
    background_pad = background_style.get("pad", 1.1)
    background = shapely.affinity.scale(
        box(*shapely.ops.unary_union(gdfs["perimeter"].geometry).bounds),
        background_pad,
        background_pad,
    )
    
    dilate = background_style.get("dilate")
    if dilate is not None:
        background = background.buffer(dilate)
    
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
    fig: Optional[matplotlib.figure.Figure] = None,
    ax: Optional[matplotlib.axes.Axes] = None,
    **kwargs
) -> Plot:
    """Draw a map from OpenStreetMap data."""
    # Default minimalist style if no style provided
    if style is None:
        style = get_style('minimal')
    elif isinstance(style, str):
        style = get_style(style)
    
    # Default layers if none provided
    layers = layers or {
        'perimeter': {},
        'water': {},
        'waterway': {},
        'streets': {
            'width': {
                'motorway': 4.5,
                'trunk': 4,
                'primary': 3.2,
                'secondary': 2.4,
                'tertiary': 1.8,
                'residential': 1.4
            }
        },
        'bridges': {},
        'building': {'tags': {'building': True}}
    }
    
    # Initialize matplotlib figure and axis
    # Fetch geodataframes
    gdfs = get_gdfs(query, layers, radius, dilate, use_cache=use_cache, auto_optimize=auto_optimize)

    if mode == "matplotlib":
        if ax is None:
            fig = fig or plt.figure(figsize=figsize, dpi=300)
            ax = fig.add_subplot(111, aspect="equal")
        else:
            fig = fig or ax.figure
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
        background_style = style.get("background", {})
        if background_style:
            zorder = background_style.get("zorder", -1)
            background_kwargs = {k: v for k, v in background_style.items() if k not in ("dilate", "zorder")}
            ax.add_patch(
                PolygonPatch(
                    background,
                    **background_kwargs,
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
    fig = plt.figure(figsize=figsize, dpi=300)
    ax = plt.subplot(111, aspect="equal")
    
    mode = "plotter" if kwargs.get("plotter") else "matplotlib"
    
    plots = [
        plot(
            subplot.query,
            fig=fig,
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
