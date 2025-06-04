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
        },
        'styles': {
            'minimal': {
                'perimeter': {'fill': False, 'lw': 0, 'zorder': 0},
                'background': {'fc': '#fff', 'zorder': -1},
                'streets': {'ec': '#000', 'lw': 0.5, 'zorder': 4},
                'building': {'ec': '#000', 'fc': '#fff', 'lw': 0.5, 'zorder': 5},
                'water': {'ec': '#000', 'fc': '#fff', 'lw': 0.5, 'zorder': 3}
            },
            'blueprint': {
                'perimeter': {'fill': False, 'lw': 0, 'zorder': 0},
                'background': {'fc': '#1e3a8a', 'zorder': -1},
                'streets': {'ec': '#fff', 'lw': 0.8, 'zorder': 4},
                'building': {'ec': '#fff', 'fc': 'none', 'lw': 0.6, 'zorder': 5},
                'water': {'ec': '#3b82f6', 'fc': '#3b82f6', 'lw': 0.5, 'zorder': 3}
            },
            'vintage': {
                'perimeter': {'fill': False, 'lw': 0, 'zorder': 0},
                'background': {'fc': '#f5f5dc', 'zorder': -1},
                'streets': {'ec': '#8b4513', 'lw': 0.6, 'zorder': 4},
                'building': {'ec': '#654321', 'fc': '#deb887', 'lw': 0.4, 'zorder': 5},
                'water': {'ec': '#4682b4', 'fc': '#87ceeb', 'lw': 0.5, 'zorder': 3}
            }
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
    if style_name in config['styles']:
        style = config['styles'][style_name]
    else:
        logger.warning("Style '%s' not found, using minimal", style_name)
        style = config['styles']['minimal']
    
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
            logger.info(
                "Map saved to %s (%.2fs)",
                output_path,
                end_time - start_time,
            )
            
        else:
            logger.error("Could not create map")
            
    except Exception as e:
        logger.error("Error creating map: %s", e)
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
    style = config['styles'].get(style_name, config['styles']['minimal'])
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


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Umap - Create beautiful maps from OpenStreetMap data'
    )
    parser.add_argument(
        '-v',
        '--verbose',
        action='count',
        default=0,
        help='Increase output verbosity (use -vv for debug)',
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create a single map')
    create_parser.add_argument('--coords', help='Coordinates in lat,lon format (e.g., "40.66,29.28")')
    create_parser.add_argument('--address', help='Address or place name')
    create_parser.add_argument('--radius', type=int, help='Radius in meters (default: 5000)')
    create_parser.add_argument('--style', help='Style name (minimal, blueprint, vintage)')
    create_parser.add_argument('--output', help='Output file path')
    create_parser.add_argument('--dpi', type=int, help='DPI for output image (default: 300)')
    create_parser.add_argument('--config', help='Path to config file')
    
    # Batch command
    batch_parser = subparsers.add_parser('batch', help='Process multiple locations')
    batch_parser.add_argument('--file', required=True, help='File with locations (name,lat,lon,radius per line)')
    batch_parser.add_argument('--style', help='Style name for all maps')
    batch_parser.add_argument('--format', help='Output format (png, jpg)')
    batch_parser.add_argument('--dpi', type=int, help='DPI for output images')
    batch_parser.add_argument('--config', help='Path to config file')
    
    args = parser.parse_args()

    log_level = logging.WARNING
    if args.verbose == 1:
        log_level = logging.INFO
    elif args.verbose >= 2:
        log_level = logging.DEBUG
    logging.basicConfig(level=log_level, format='%(message)s')
    
    if args.command == 'create':
        create_map(args)
    elif args.command == 'batch':
        batch_process(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main() 