"""Optimization utilities for Umap."""
from typing import Dict, Any, List
import geopandas as gp


def auto_optimize_layers(radius: float) -> Dict[str, Any]:
    """Automatically optimize layer configuration based on radius.
    
    Args:
        radius: Map radius in meters
        
    Returns:
        Optimized layer configuration
    """
    if radius < 1000:
        # High detail for small areas
        return {
            'detail': 'high',
            'include_footways': True,
            'include_small_buildings': True,
            'min_building_area': 10,
            'street_width_scale': 1.0,
            'include_minor_water': True
        }
    elif radius < 5000:
        # Medium detail for medium areas
        return {
            'detail': 'medium',
            'include_footways': False,
            'include_small_buildings': True,
            'min_building_area': 50,
            'street_width_scale': 1.2,
            'include_minor_water': False
        }
    elif radius < 15000:
        # Low detail for large areas
        return {
            'detail': 'low',
            'include_footways': False,
            'include_small_buildings': False,
            'min_building_area': 200,
            'street_width_scale': 1.5,
            'major_roads_only': True,
            'include_minor_water': False
        }
    else:
        # Very low detail for very large areas
        return {
            'detail': 'very_low',
            'include_footways': False,
            'include_small_buildings': False,
            'min_building_area': 1000,
            'street_width_scale': 2.0,
            'major_roads_only': True,
            'highways_only': True,
            'include_minor_water': False
        }


def smart_filter_gdf(gdf: gp.GeoDataFrame, layer_type: str, radius: float, optimization_config: Dict[str, Any]) -> gp.GeoDataFrame:
    """Apply smart filtering to GeoDataFrame based on layer type and optimization config.
    
    Args:
        gdf: GeoDataFrame to filter
        layer_type: Type of layer ('building', 'streets', 'water', etc.)
        radius: Map radius in meters
        optimization_config: Optimization configuration from auto_optimize_layers
        
    Returns:
        Filtered GeoDataFrame
    """
    if gdf.empty:
        return gdf
    
    filtered_gdf = gdf.copy()
    
    if layer_type == 'building':
        # Filter buildings by area (in square meters)
        min_area = optimization_config.get('min_building_area', 50)
        try:
            projected = filtered_gdf.to_crs(epsg=3857)
            filtered_gdf['area_m2'] = projected.geometry.area
        except Exception:
            # Fallback without CRS; may be inaccurate
            filtered_gdf['area_m2'] = filtered_gdf.geometry.area
        filtered_gdf = filtered_gdf[filtered_gdf['area_m2'] >= min_area]
        
        # For very large areas, keep only important buildings
        if radius > 15000 and 'building' in filtered_gdf.columns:
            important_buildings = ['commercial', 'industrial', 'public', 'hospital', 'school']
            mask = filtered_gdf['building'].isin(important_buildings) | (filtered_gdf['area_m2'] > 2000)
            filtered_gdf = filtered_gdf[mask]
    
    elif layer_type == 'streets':
        # Filter streets by importance
        if 'highway' in filtered_gdf.columns:
            if optimization_config.get('highways_only', False):
                # Only major highways
                major_highways = ['motorway', 'trunk']
                filtered_gdf = filtered_gdf[filtered_gdf['highway'].isin(major_highways)]
            elif optimization_config.get('major_roads_only', False):
                # Major roads only
                major_roads = ['motorway', 'trunk', 'primary', 'secondary']
                filtered_gdf = filtered_gdf[filtered_gdf['highway'].isin(major_roads)]
            elif not optimization_config.get('include_footways', True):
                # Exclude footways and paths
                exclude_types = ['footway', 'path', 'steps', 'cycleway']
                filtered_gdf = filtered_gdf[~filtered_gdf['highway'].isin(exclude_types)]
    
    elif layer_type == 'water':
        # Filter water features
        if not optimization_config.get('include_minor_water', True):
            # Only keep major water bodies (area in square meters)
            try:
                projected = filtered_gdf.to_crs(epsg=3857)
                filtered_gdf['area_m2'] = projected.geometry.area
            except Exception:
                filtered_gdf['area_m2'] = filtered_gdf.geometry.area
            filtered_gdf = filtered_gdf[filtered_gdf['area_m2'] >= 1000]
    
    return filtered_gdf


def optimize_layer_config(layers: Dict[str, Any], radius: float) -> Dict[str, Any]:
    """Optimize layer configuration based on radius.
    
    Args:
        layers: Original layer configuration
        radius: Map radius in meters
        
    Returns:
        Optimized layer configuration
    """
    optimization_config = auto_optimize_layers(radius)
    optimized_layers = layers.copy()
    
    # Apply street width scaling
    if 'streets' in optimized_layers:
        width_scale = optimization_config.get('street_width_scale', 1.0)
        if 'width' in optimized_layers['streets']:
            for road_type, width in optimized_layers['streets']['width'].items():
                optimized_layers['streets']['width'][road_type] = width * width_scale
    
    # Add optimization flags to each layer
    for layer_name in optimized_layers:
        if layer_name not in ['perimeter']:
            optimized_layers[layer_name]['_optimization'] = optimization_config
    
    return optimized_layers


def get_processing_stats(gdfs: Dict[str, gp.GeoDataFrame]) -> Dict[str, Any]:
    """Get processing statistics for GeoDataFrames.
    
    Args:
        gdfs: Dictionary of GeoDataFrames
        
    Returns:
        Dictionary with statistics
    """
    stats = {}
    
    for layer_name, gdf in gdfs.items():
        if layer_name == 'perimeter':
            continue
            
        layer_stats = {
            'feature_count': len(gdf),
            'empty_geometries': gdf.geometry.is_empty.sum() if not gdf.empty else 0,
            'invalid_geometries': (~gdf.geometry.is_valid).sum() if not gdf.empty else 0
        }
        
        # Add area statistics for polygon layers
        if not gdf.empty and gdf.geometry.iloc[0].geom_type in ['Polygon', 'MultiPolygon']:
            try:
                areas = gdf.to_crs(epsg=3857).geometry.area
            except Exception:
                areas = gdf.geometry.area
            layer_stats.update({
                'total_area': areas.sum(),  # square meters
                'avg_area': areas.mean(),   # square meters
                'min_area': areas.min(),    # square meters
                'max_area': areas.max()     # square meters
            })
        
        # Add length statistics for line layers
        elif not gdf.empty and gdf.geometry.iloc[0].geom_type in ['LineString', 'MultiLineString']:
            try:
                lengths = gdf.to_crs(epsg=3857).geometry.length
            except Exception:
                lengths = gdf.geometry.length
            layer_stats.update({
                'total_length': lengths.sum(),  # meters
                'avg_length': lengths.mean(),   # meters
                'min_length': lengths.min(),    # meters
                'max_length': lengths.max()     # meters
            })
        
        stats[layer_name] = layer_stats
    
    return stats


def check_data_quality(gdfs: Dict[str, gp.GeoDataFrame]) -> Dict[str, Any]:
    """Check data quality and report issues.
    
    Args:
        gdfs: Dictionary of GeoDataFrames
        
    Returns:
        Quality report dictionary
    """
    report = {
        'overall_quality': 'good',
        'issues': [],
        'layer_reports': {}
    }
    
    total_features = 0
    total_issues = 0
    
    for layer_name, gdf in gdfs.items():
        if layer_name == 'perimeter':
            continue
        
        layer_report = {
            'feature_count': len(gdf),
            'issues': []
        }
        
        total_features += len(gdf)
        
        if gdf.empty:
            layer_report['issues'].append('No data found')
            total_issues += 1
        else:
            # Check for empty geometries
            empty_count = gdf.geometry.is_empty.sum()
            if empty_count > 0:
                layer_report['issues'].append(f'{empty_count} empty geometries')
                total_issues += empty_count
            
            # Check for invalid geometries
            invalid_count = (~gdf.geometry.is_valid).sum()
            if invalid_count > 0:
                layer_report['issues'].append(f'{invalid_count} invalid geometries')
                total_issues += invalid_count
            
            # Check for very small features that might be noise
            if gdf.geometry.iloc[0].geom_type in ['Polygon', 'MultiPolygon']:
                try:
                    areas = gdf.to_crs(epsg=3857).geometry.area
                except Exception:
                    areas = gdf.geometry.area
                very_small = (areas < 1).sum()
                if very_small > len(gdf) * 0.1:  # More than 10% are very small
                    layer_report['issues'].append(f'{very_small} very small features (possible noise)')
        
        report['layer_reports'][layer_name] = layer_report
    
    # Determine overall quality
    if total_features == 0:
        report['overall_quality'] = 'no_data'
        report['issues'].append('No data available for any layer')
    elif total_issues > total_features * 0.1:  # More than 10% issues
        report['overall_quality'] = 'poor'
        report['issues'].append(f'High issue rate: {total_issues}/{total_features} features have problems')
    elif total_issues > 0:
        report['overall_quality'] = 'fair'
        report['issues'].append(f'Some issues found: {total_issues} problematic features')
    
    return report 