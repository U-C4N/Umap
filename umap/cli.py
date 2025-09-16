"""Command line interface for Umap."""
import argparse
import sys
import os
from pathlib import Path
import yaml
import time
import logging
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

from .core.plot import plot
from .utils.drawing import add_frame, add_north_arrow, add_scale_bar, add_legend_simple
from .utils.styles import get_style, list_styles


def parse_coordinates(coord_str: str) -> Tuple[float, float]:
    """Parse coordinate string like '40.66,29.28' to tuple."""
    try:
        lat, lon = map(float, coord_str.split(','))
        return (lat, lon)
    except ValueError:
        raise ValueError(f"Invalid coordinate format: {coord_str}. Use 'lat,lon' format.")


def load_config(config_path: Optional[str] = None) -> Dict:
    """Load configuration from YAML file."""
    if config_path is None:
        config_path = os.path.expanduser("~/.umap/config.yaml")
    
    default_config = {
        'default': {
            'style': 'minimal',
            'dpi': 300,
            'format': 'jpg',
            'cache_enabled': True,
            'radius': 5000
        }
    }
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = yaml.safe_load(f)
                # Merge with defaults
                default_config.update(user_config)
        except Exception as e:
            logger.warning("Could not load config file: %s", e)
    
    return default_config





def create_simple_map(args):
    """Create a single map with simplified arguments."""
    config = load_config(None)
    defaults = config.get('default', {})

    # Determine output format
    output_format = args.format or defaults.get('format', 'jpg')
    
    # Parse location - handle both location name and coordinates
    if args.coords:
        location = parse_coordinates(args.coords)
        location_name = f"coords_{args.coords.replace(',', '_')}"
    elif args.location:
        location = args.location
        location_name = args.location.replace(" ", "_").replace(",", "_")
    else:
        raise ValueError("Either location name or coordinates must be provided")
    
    # Get style - check for style shortcuts first
    style_name = args.style or defaults.get('style', 'minimal')
    
    # Handle style shortcuts
    if args.blueprint:
        style_name = 'blueprint'
    elif args.vintage:
        style_name = 'vintage'
    elif args.minimal:
        style_name = 'minimal'
    
    try:
        style = get_style(style_name)
    except KeyError:
        style = get_style('minimal')
    
    # Create plot
    radius = args.radius if args.radius is not None else defaults.get('radius', 5000)
    dpi = defaults.get('dpi', 300)
    use_cache = defaults.get('cache_enabled', True)
    
    print(f"Creating map for {location}...")
    start_time = time.time()
    
    try:
        map_plot = plot(
            location,
            radius=radius,
            style=style,
            figsize=(12, 12),
            use_cache=use_cache
        )
        
        if map_plot.fig and map_plot.ax:
            # Add frame
            add_frame(map_plot.ax)
            # Add extras
            add_north_arrow(map_plot.ax)
            add_scale_bar(map_plot.ax, length_km=max(1, int(radius/2000)))
            add_legend_simple(map_plot.ax, style)
            
            # Determine output path - default to current working directory
            if args.output:
                output_path = args.output
                if not os.path.splitext(output_path)[1]:
                    output_path = f"{output_path}.{output_format}"
            else:
                # Save to current working directory
                output_filename = f"{location_name}_map.{output_format}"
                output_path = os.path.join(os.getcwd(), output_filename)

            map_plot.fig.savefig(
                output_path,
                dpi=dpi,
                bbox_inches='tight',
                facecolor='#fff',
                pad_inches=0.5,
                format=output_format
            )
            
            end_time = time.time()
            print(f"Map completed! Saved to: {output_path} ({end_time - start_time:.1f}s)")
            
        else:
            print("Error: Could not create map")
            
    except Exception as e:
        print(f"Error creating map: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Create maps from OpenStreetMap data',
        epilog='Examples:\n  umap Istanbul\n  umap "New York"\n  umap Istanbul --blueprint\n  umap "New York" --vintage --radius 10000',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Simple address/city argument (positional)
    parser.add_argument(
        'location',
        nargs='?',
        help='City name to map'
    )
    
    # Optional arguments
    parser.add_argument(
        '--coords',
        help='Coordinates: "lat,lon"'
    )
    parser.add_argument(
        '--radius',
        type=int,
        default=None,
        help='Radius in meters (default: config or 5000)'
    )
    parser.add_argument(
        '--style',
        default=None,
        help='Style: minimal, blueprint, vintage (default: config or minimal)'
    )
    parser.add_argument(
        '--blueprint',
        action='store_true',
        help='Use blueprint style (shortcut for --style blueprint)'
    )
    parser.add_argument(
        '--vintage',
        action='store_true',
        help='Use vintage style (shortcut for --style vintage)'
    )
    parser.add_argument(
        '--minimal',
        action='store_true',
        help='Use minimal style (shortcut for --style minimal)'
    )
    parser.add_argument(
        '--format',
        choices=['png', 'jpg', 'svg', 'pdf'],
        help='Output format (default: jpg)'
    )
    parser.add_argument(
        '--output',
        help='Output file path'
    )
    
    args = parser.parse_args()

    # Handle simple location mapping (main use case)
    if not args.location and not args.coords:
        parser.print_help()
        print("\nError: Please provide a location name or coordinates.")
        sys.exit(1)
    
    # Create map with simplified arguments
    create_simple_map(args)


if __name__ == '__main__':
    main()
