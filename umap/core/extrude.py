"""Pseudo-3D (2.5D) building extrusion rendering.

Buildings are extruded along a fixed screen-space direction using their
OSM ``building:levels`` (or ``height``) tags, producing an isometric
"paper model" look with shaded walls, lit roofs and soft drop shadows.
"""
import logging
import math
import numpy as np
import matplotlib.colors as mcolors
from matplotlib.path import Path
from matplotlib.patches import PathPatch, Polygon as MplPolygon
from matplotlib.collections import PatchCollection
from shapely.geometry import Polygon, MultiPolygon
import shapely.affinity

logger = logging.getLogger(__name__)

_MAX_LEVELS = 40
_METERS_PER_LEVEL = 3.0


def _parse_levels(levels_value, height_value, default_levels: float) -> float:
    """Parse a building's floor count from OSM tags, falling back to height."""
    raw = levels_value
    if isinstance(raw, list) and raw:
        raw = raw[0]
    if raw is not None:
        try:
            value = float(str(raw).split(";")[0].strip())
            if value > 0:
                return min(value, _MAX_LEVELS)
        except (ValueError, TypeError):
            pass

    raw = height_value
    if isinstance(raw, list) and raw:
        raw = raw[0]
    if raw is not None:
        try:
            meters = float(str(raw).lower().replace("m", "").strip())
            if meters > 0:
                return min(meters / _METERS_PER_LEVEL, _MAX_LEVELS)
        except (ValueError, TypeError):
            pass

    return default_levels


def _blend(color, other, t: float):
    c1 = np.array(mcolors.to_rgb(color))
    c2 = np.array(mcolors.to_rgb(other))
    return tuple((1 - t) * c1 + t * c2)


def _roof_patch(poly: Polygon) -> PathPatch:
    """Build a PathPatch for a polygon, preserving interior holes."""
    rings = [np.asarray(poly.exterior.coords)[:, :2]]
    rings += [np.asarray(ring.coords)[:, :2] for ring in poly.interiors]
    codes = []
    for ring in rings:
        codes += [Path.MOVETO] + [Path.LINETO] * (len(ring) - 2) + [Path.CLOSEPOLY]
    return PathPatch(Path(np.concatenate(rings), codes))


def plot_extruded_buildings(gdf, ax, config, span, clip_patch=None, zorder=5):
    """Render buildings as pseudo-3D extrusions on a matplotlib axis.

    Args:
        gdf: GeoDataFrame with building footprints (WGS84).
        ax: Target matplotlib axis.
        config: The ``extrude`` style dictionary (direction, scale, colors...).
        span: Map extent in data units, used to size one building level.
        clip_patch: Optional patch to clip drawing to the land perimeter.
        zorder: Base z-order for the building collection.
    """
    if gdf is None or gdf.empty:
        return

    direction = math.radians(config.get("direction", 62))
    d = np.array([math.cos(direction), math.sin(direction)])
    light = np.array([
        math.cos(direction + math.pi / 2),
        math.sin(direction + math.pi / 2),
    ])

    unit = span * config.get("scale", 0.0018)
    default_levels = config.get("default_levels", 2)
    wall_fc = config.get("wall_fc", "#d9cfba")
    roof_fc = config.get("roof_fc", "#fffdf7")
    roof_ec = config.get("roof_ec", "#c4b89e")
    roof_lw = config.get("roof_lw", 0.25)
    shadow_fc = config.get("shadow_fc", "#8a8577")
    shadow_alpha = config.get("shadow_alpha", 0.18)

    simplify_tol = span * 5e-5

    levels_col = gdf["building:levels"] if "building:levels" in gdf.columns else None
    height_col = gdf["height"] if "height" in gdf.columns else None

    items = []
    for i, geom in enumerate(gdf.geometry.values):
        if geom is None or geom.is_empty:
            continue
        levels = _parse_levels(
            levels_col.iloc[i] if levels_col is not None else None,
            height_col.iloc[i] if height_col is not None else None,
            default_levels,
        )
        polys = list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]
        for poly in polys:
            if not isinstance(poly, Polygon):
                continue
            poly = poly.simplify(simplify_tol, preserve_topology=True)
            if poly.is_empty or not isinstance(poly, Polygon) or poly.exterior is None:
                continue
            centroid = poly.centroid
            projection = centroid.x * d[0] + centroid.y * d[1]
            items.append((projection, poly, levels * unit))

    if not items:
        return

    # Cap the number of extruded buildings to keep render time sane in
    # dense cities; the largest footprints (landmarks) are kept.
    max_buildings = int(config.get("max_buildings", 8000))
    if len(items) > max_buildings:
        items.sort(key=lambda item: -item[1].area)
        items = items[:max_buildings]

    # Paint far-to-near along the extrusion axis so closer buildings
    # correctly overlap the ones behind them.
    items.sort(key=lambda item: -item[0])

    wall_light = _blend(wall_fc, "#ffffff", 0.35)
    wall_dark = _blend(wall_fc, "#000000", 0.18)
    roof_rgb = mcolors.to_rgb(roof_fc)

    shadow_patches = []
    patches, facecolors, edgecolors, linewidths = [], [], [], []

    for _, poly, h in items:
        off = d * h
        exterior = np.asarray(poly.exterior.coords)[:, :2]

        shadow_patches.append(MplPolygon(exterior - d * (h * 0.4), closed=True))

        # Walls: one quad per exterior edge, two-tone shaded by orientation.
        for p1, p2 in zip(exterior[:-1], exterior[1:]):
            edge = p2 - p1
            normal = np.array([edge[1], -edge[0]])
            norm = np.linalg.norm(normal)
            if norm == 0:
                continue
            facing_light = float(np.dot(normal / norm, light)) > 0
            patches.append(
                MplPolygon(np.array([p1, p2, p2 + off, p1 + off]), closed=True)
            )
            facecolors.append(wall_light if facing_light else wall_dark)
            edgecolors.append("none")
            linewidths.append(0.0)

        roof = shapely.affinity.translate(poly, xoff=off[0], yoff=off[1])
        patches.append(_roof_patch(roof))
        facecolors.append(roof_rgb)
        edgecolors.append(roof_ec)
        linewidths.append(roof_lw)

    shadow_collection = PatchCollection(
        shadow_patches,
        facecolors=shadow_fc,
        edgecolors="none",
        alpha=shadow_alpha,
        zorder=zorder - 0.2,
    )
    ax.add_collection(shadow_collection)

    building_collection = PatchCollection(
        patches,
        facecolors=facecolors,
        edgecolors=edgecolors,
        linewidths=linewidths,
        zorder=zorder,
    )
    ax.add_collection(building_collection)

    if clip_patch is not None:
        shadow_collection.set_clip_path(clip_patch)
        building_collection.set_clip_path(clip_patch)

    logger.info("Extruded %d building polygons", len(items))
