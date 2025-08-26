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
from .utils.drawing import add_frame
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
            'format': 'png',
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


def create_map(args):
    """Create a single map."""
    config = load_config(args.config)
    
    # Parse coordinates or address
    if args.coords:
        location = parse_coordinates(args.coords)
    elif args.address:
        location = args.address
    else:
        raise ValueError("Either --coords or --address must be provided")
    
    # Get style
    style_name = args.style or config['default']['style']
    try:
        style = get_style(style_name)
    except KeyError:
        logger.warning("Style '%s' not found, using minimal", style_name)
        style = get_style('minimal')
    
    # Create plot
    radius = args.radius or config['default']['radius']
    dpi = args.dpi or config['default']['dpi']
    
    logger.info("Creating map for %s with radius %sm...", location, radius)
    start_time = time.time()
    
    try:
        map_plot = plot(
            location,
            radius=radius,
            style=style,
            figsize=(12, 12)
        )
        
        if map_plot.fig and map_plot.ax:
            # Add frame
            add_frame(map_plot.ax)
            
            # Save
            output_path = args.output or f"map.{config['default']['format']}"
            map_plot.fig.savefig(
                output_path,
                dpi=dpi,
                bbox_inches='tight',
                facecolor='#fff',
                pad_inches=0.5
            )
            
            end_time = time.time()
            print(f"Map completed! Saved to: {output_path} ({end_time - start_time:.1f}s)")
            
        else:
            print("Error: Could not create map")
            
    except Exception as e:
        print(f"Error creating map: {e}")
        sys.exit(1)


def batch_process(args):
    """Process multiple locations from file."""
    config = load_config(args.config)
    
    if not os.path.exists(args.file):
        logger.error("File %s not found", args.file)
        sys.exit(1)
    
    # Read locations file
    locations = []
    with open(args.file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            try:
                parts = line.split(',')
                if len(parts) >= 3:
                    name = parts[0].strip()
                    lat = float(parts[1].strip())
                    lon = float(parts[2].strip())
                    radius = int(parts[3].strip()) if len(parts) > 3 else config['default']['radius']
                    locations.append({
                        'name': name,
                        'coords': (lat, lon),
                        'radius': radius
                    })
                else:
                    logger.warning(
                        "Invalid format at line %s: %s", line_num, line
                    )
            except ValueError as e:
                logger.warning("Error parsing line %s: %s", line_num, e)
    
    if not locations:
        logger.error("No valid locations found in file")
        sys.exit(1)
    
    # Process each location
    style_name = args.style or config['default']['style']
    try:
        style = get_style(style_name)
    except KeyError:
        logger.warning("Style '%s' not found, using minimal", style_name)
        style = get_style('minimal')
    dpi = args.dpi or config['default']['dpi']
    
    logger.info("Processing %s locations...", len(locations))
    
    for i, loc in enumerate(locations, 1):
        logger.info(
            "[%s/%s] Creating map for %s...", i, len(locations), loc["name"]
        )
        
        try:
            map_plot = plot(
                loc['coords'],
                radius=loc['radius'],
                style=style,
                figsize=(12, 12)
            )
            
            if map_plot.fig and map_plot.ax:
                add_frame(map_plot.ax)
                
                output_path = f"{loc['name']}.{args.format or config['default']['format']}"
                map_plot.fig.savefig(
                    output_path,
                    dpi=dpi,
                    bbox_inches='tight',
                    facecolor='#fff',
                    pad_inches=0.5
                )
                logger.info("  Saved: %s", output_path)
            else:
                logger.error("  Could not create map for %s", loc["name"])
                
        except Exception as e:
            logger.error("  Error processing %s: %s", loc["name"], e)


def get_desktop_path():
    """Get the path to desktop directory."""
    import platform
    if platform.system() == "Windows":
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    else:
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    
    # Create desktop directory if it doesn't exist
    os.makedirs(desktop, exist_ok=True)
    return desktop


def create_simple_map(args):
    """Create a single map with simplified arguments."""
    config = load_config(args.config)
    
    # Parse location - handle both location name and coordinates
    if args.coords:
        location = parse_coordinates(args.coords)
        location_name = f"coords_{args.coords.replace(',', '_')}"
    elif args.location:
        location = args.location
        location_name = args.location.replace(" ", "_").replace(",", "_")
    else:
        raise ValueError("Either location name or coordinates must be provided")
    
    # Get style
    style_name = args.style or config['default']['style']
    try:
        style = get_style(style_name)
    except KeyError:
        logger.warning("Style '%s' not found, using minimal", style_name)
        style = get_style('minimal')
    
    # Create plot
    radius = args.radius or config['default']['radius']
    dpi = args.dpi or config['default']['dpi']
    
    print(f"Creating map for {location}...")
    start_time = time.time()
    
    try:
        map_plot = plot(
            location,
            radius=radius,
            style=style,
            figsize=(12, 12)
        )
        
        if map_plot.fig and map_plot.ax:
            # Add frame
            add_frame(map_plot.ax)
            
            # Determine output path - default to Desktop
            if args.output:
                output_path = args.output
            else:
                desktop_path = get_desktop_path()
                output_filename = f"{location_name}_map.{config['default']['format']}"
                output_path = os.path.join(desktop_path, output_filename)
            
            map_plot.fig.savefig(
                output_path,
                dpi=dpi,
                bbox_inches='tight',
                facecolor='#fff',
                pad_inches=0.5
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
        description='Umap - Create beautiful maps from OpenStreetMap data',
        epilog='Examples:\n  umap Istanbul\n  umap "New York"\n  umap --coords "40.66,29.28"',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Simple address/city argument (positional)
    parser.add_argument(
        'location',
        nargs='?',
        help='City name or address to map (e.g., "Istanbul", "New York")'
    )
    
    # Optional arguments
    parser.add_argument(
        '--coords',
        help='Coordinates in lat,lon format (e.g., "40.66,29.28")'
    )
    parser.add_argument(
        '--radius',
        type=int,
        default=5000,
        help='Radius in meters (default: 5000)'
    )
    parser.add_argument(
        '--style',
        default='minimal',
        help='Style name (minimal, blueprint, vintage, default: minimal)'
    )
    parser.add_argument(
        '--output',
        help='Output file path (default: Desktop/[location_name]_map.png)'
    )
    parser.add_argument(
        '--dpi',
        type=int,
        default=300,
        help='DPI for output image (default: 300)'
    )
    parser.add_argument(
        '--config',
        help='Path to config file'
    )
    parser.add_argument(
        '-v',
        '--verbose',
        action='count',
        default=0,
        help='Increase output verbosity (use -vv for debug)'
    )
    
    args = parser.parse_args()

    # Set up logging
    log_level = logging.WARNING
    if args.verbose == 1:
        log_level = logging.INFO
    elif args.verbose >= 2:
        log_level = logging.DEBUG
    logging.basicConfig(level=log_level, format='%(message)s')
    
    # Check for batch mode via special argument
    if len(sys.argv) > 1 and sys.argv[1] == 'batch':
        # Handle batch processing with a separate parser
        batch_parser = argparse.ArgumentParser(
            description='Batch process multiple locations'
        )
        batch_parser.add_argument('command', help='batch command')
        batch_parser.add_argument('--file', required=True, help='File with locations (name,lat,lon,radius per line)')
        batch_parser.add_argument('--style', help='Style name for all maps')
        batch_parser.add_argument('--format', help='Output format (png, jpg)')
        batch_parser.add_argument('--dpi', type=int, help='DPI for output images')
        batch_parser.add_argument('--config', help='Path to config file')
        
        batch_args = batch_parser.parse_args()
        batch_process(batch_args)
        return
    
    # Handle simple location mapping (main use case)
    if not args.location and not args.coords:
        parser.print_help()
        print("\nError: Please provide a location name or coordinates.")
        print("Examples:")
        print("  umap Istanbul")
        print("  umap \"New York\"")
        print("  umap --coords \"40.66,29.28\"")
        sys.exit(1)
    
    # Create map with simplified arguments
    create_simple_map(args)


if __name__ == '__main__':
    main()