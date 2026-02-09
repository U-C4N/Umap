"""OpenStreetMap data fetching functionality."""
import re
import logging
import numpy as np
import osmnx as ox
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from shapely.geometry import (
    box,
    Point,
    Polygon,
    MultiPolygon,
    LineString,
    MultiLineString,
)
from geopandas import GeoDataFrame
from shapely.affinity import rotate, scale
from shapely.ops import unary_union
from shapely.strtree import STRtree
from ..utils.cache import get_cache
from ..utils.optimization import optimize_layer_config, smart_filter_gdf

logger = logging.getLogger(__name__)

def _transform_to_web_mercator(gdf):
    """Transform GeoDataFrame to Web Mercator (EPSG:3857)."""
    return gdf.to_crs(epsg=3857) if gdf.crs != 'EPSG:3857' else gdf

def _transform_to_wgs84(gdf):
    """Transform GeoDataFrame to WGS84 (EPSG:4326)."""
    return gdf.to_crs(4326) if gdf.crs != 'EPSG:4326' else gdf

def parse_query(query):
    """Parse query type (coordinates, OSMId, or address)."""
    if isinstance(query, GeoDataFrame):
        return "polygon"
    elif isinstance(query, tuple):
        return "coordinates"
    elif re.match("""[A-Z][0-9]+""", query):
        return "osmid"
    else:
        return "address"

def get_boundary(query, radius, circle=False, rotation=0):
    """Get circular or square boundary around point."""
    # Get point from query
    point = query if parse_query(query) == "coordinates" else ox.geocode(query)
    # Create GeoDataFrame from point and project
    boundary = GeoDataFrame(geometry=[Point(point[::-1])], crs="EPSG:4326")
    boundary = _transform_to_web_mercator(boundary)

    if circle:  # Circular shape
        # use .buffer() to expand point into circle
        boundary.geometry = boundary.geometry.buffer(radius)
    else:  # Square shape
        x, y = np.concatenate(boundary.geometry[0].xy)
        r = radius
        boundary = GeoDataFrame(
            geometry=[
                rotate(
                    Polygon(
                        [(x - r, y - r), (x + r, y - r), (x + r, y + r), (x - r, y + r)]
                    ),
                    rotation,
                )
            ],
            crs=boundary.crs,
        )

    # Unproject
    boundary = _transform_to_wgs84(boundary)
    return boundary

def get_perimeter(
    query,
    radius=None,
    by_osmid=False,
    circle=False,
    dilate=None,
    rotation=0,
    aspect_ratio=1,
    **kwargs
):
    """Get perimeter from query."""
    if radius:
        # Perimeter is a circular or square shape
        perimeter = get_boundary(query, radius, circle=circle, rotation=rotation)
    else:
        # Perimeter is a OSM or user-provided polygon
        if parse_query(query) == "polygon":
            # Perimeter was already provided
            perimeter = query
        else:
            # Fetch perimeter from OSM
            perimeter = ox.geocode_to_gdf(
                query,
                by_osmid=by_osmid,
                **kwargs,
            )

    # Scale according to aspect ratio
    perimeter = _transform_to_web_mercator(perimeter)
    perimeter.loc[0, "geometry"] = scale(perimeter.loc[0, "geometry"], aspect_ratio, 1)
    
    # Apply dilation if needed
    if dilate is not None:
        perimeter.geometry = perimeter.geometry.buffer(dilate)
    
    perimeter = _transform_to_wgs84(perimeter)

    return perimeter

def get_gdf(
    layer,
    perimeter,
    perimeter_tolerance=0,
    tags=None,
    osmid=None,
    custom_filter=None,
    union=False,
    **kwargs
):
    """Get a GeoDataFrame for a specific layer."""
    try:
        # Project and apply tolerance to perimeter
        perimeter_projected = _transform_to_web_mercator(perimeter)
        perimeter_with_tolerance = perimeter_projected.buffer(perimeter_tolerance)
        perimeter_with_tolerance = _transform_to_wgs84(perimeter_with_tolerance)
        perimeter_with_tolerance = unary_union(perimeter_with_tolerance.geometry).buffer(0)
        
        # Get bounding box
        bbox = box(*perimeter_with_tolerance.bounds)
        
        # Fetch data based on layer type
        if layer in ["streets", "railway"]:
            try:
                graph = ox.graph_from_polygon(
                    bbox,
                    retain_all=True,
                    custom_filter=custom_filter,
                    truncate_by_edge=True,
                )
                gdf = ox.graph_to_gdfs(graph, nodes=False)
            except (ConnectionError, TimeoutError) as e:
                logger.warning("Network error fetching %s data: %s", layer, e)
                gdf = GeoDataFrame(geometry=[])
            except Exception as e:
                logger.warning("Error fetching %s data: %s", layer, e)
                gdf = GeoDataFrame(geometry=[])
        elif layer == "coastline":
            try:
                # Fetch coastline geometries from OSM
                gdf = ox.features_from_polygon(
                    bbox, tags={"natural": "coastline"}
                )
            except Exception as e:
                logger.warning("Error fetching coastline data: %s", e)
                gdf = GeoDataFrame(geometry=[])
        elif layer == "waterway":
            try:
                # Fetch linear waterways (rivers, streams, canals, etc.)
                gdf = ox.features_from_polygon(
                    bbox,
                    tags={
                        "waterway": [
                            "river",
                            "stream",
                            "canal",
                            "drain",
                            "ditch",
                        ]
                    },
                )
            except Exception as e:
                logger.warning("Error fetching waterway data: %s", e)
                gdf = GeoDataFrame(geometry=[])
        elif layer == "water":
            try:
                # Fetch water bodies including seas, bays, harbours, etc.
                gdf = ox.features_from_polygon(
                    bbox,
                    tags={
                        "natural": ["water", "bay", "strait", "wetland"],
                        "water": True,
                        "waterway": ["riverbank", "dock"],
                        "landuse": ["reservoir", "basin"],
                        "place": ["sea", "ocean"],
                        "harbour": True,
                    },
                )
            except Exception as e:
                logger.warning("Error fetching water data: %s", e)
                gdf = GeoDataFrame(geometry=[])
        elif layer == "bridges":
            try:
                # Fetch bridge features
                gdf = ox.features_from_polygon(
                    bbox,
                    tags={
                        "bridge": True,
                        "man_made": "bridge",
                    },
                )
            except Exception as e:
                logger.warning("Error fetching bridges data: %s", e)
                gdf = GeoDataFrame(geometry=[])
        else:
            try:
                if osmid is None:
                    # Fetch geometries from OSM
                    gdf = ox.features_from_polygon(
                        bbox, tags={tags: True} if isinstance(tags, str) else tags
                    )
                else:
                    gdf = ox.geocode_to_gdf(osmid, by_osmid=True)
            except Exception as e:
                logger.warning("Error fetching %s data: %s", layer, e)
                gdf = GeoDataFrame(geometry=[])
    except Exception as e:
        logger.warning("Error processing perimeter for %s: %s", layer, e)
        gdf = GeoDataFrame(geometry=[])

    # Fix invalid geometries before spatial operations
    if not gdf.empty:
        invalid_mask = ~gdf.geometry.is_valid
        if invalid_mask.any():
            gdf.loc[invalid_mask, 'geometry'] = gdf.loc[invalid_mask].geometry.buffer(0)

    # Intersect with perimeter using a spatial index
    if not gdf.empty:
        tree = STRtree(gdf.geometry.values)
        intersecting_idx = tree.query(perimeter_with_tolerance)
        gdf = gdf.iloc[intersecting_idx]

        if not gdf.empty:
            gdf = gdf.copy()
            gdf.geometry = gdf.geometry.intersection(perimeter_with_tolerance)
            gdf = gdf[~gdf.geometry.is_empty]

    return gdf

def get_gdfs(query, layers_dict, radius, dilate, rotation=0, use_cache=True, auto_optimize=True) -> dict:
    """Fetch GeoDataFrames given query and a dictionary of layers."""
    cache = get_cache()
    
    # Apply optimization if enabled and radius is provided
    if auto_optimize and radius:
        layers_dict = optimize_layer_config(layers_dict, radius)
    
    # Check cache first if enabled
    if use_cache:
        cached_data = cache.get_cached_data(query, radius or 0, layers_dict)
        if cached_data is not None:
            return cached_data
    
    perimeter_kwargs = {}
    if "perimeter" in layers_dict:
        perimeter_kwargs = deepcopy(layers_dict["perimeter"])
        perimeter_kwargs.pop("dilate", None)  # Remove dilate if exists, otherwise return None

    # Get perimeter
    perimeter = get_perimeter(
        query,
        radius=radius,
        rotation=rotation,
        dilate=dilate,
        **perimeter_kwargs,
    )

    # Get other layers as GeoDataFrames
    gdfs = {"perimeter": perimeter}
    futures = []
    # Limit thread count to avoid overloading the OSM API
    layer_count = sum(1 for k in layers_dict if k != "perimeter")
    max_workers = min(layer_count, 6)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for layer, kwargs in layers_dict.items():
            if layer != "perimeter":
                futures.append((layer, kwargs, executor.submit(get_gdf, layer, perimeter, **kwargs)))

        for layer, kwargs, future in futures:
            try:
                gdf = future.result()
            except Exception as e:
                logger.warning("Error fetching %s: %s", layer, e)
                gdf = GeoDataFrame(geometry=[])

            # Apply smart filtering if optimization is enabled
            if auto_optimize and radius and not gdf.empty:
                optimization_config = kwargs.get('_optimization', {})
                gdf = smart_filter_gdf(gdf, layer, radius, optimization_config)

            gdfs[layer] = gdf

    # Cache the results if enabled
    if use_cache:
        cache.cache_data(query, radius or 0, layers_dict, gdfs)

    return gdfs
