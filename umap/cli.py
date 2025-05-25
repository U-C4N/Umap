"""Command line interface for Umap."""
import argparse
import sys
import os
from pathlib import Path
import yaml
import time
from typing import Dict, List, Tuple, Optional

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
            print(f"Warning: Could not load config file: {e}")
    
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
        print(f"Warning: Style '{style_name}' not found, using minimal")
        style = config['styles']['minimal']
    
    # Create plot
    radius = args.radius or config['default']['radius']
    dpi = args.dpi or config['default']['dpi']
    
    print(f"Creating map for {location} with radius {radius}m...")
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
            print(f"Map saved to {output_path} ({end_time - start_time:.2f}s)")
            
        else:
            print("Error: Could not create map")
            
    except Exception as e:
        print(f"Error creating map: {e}")
        sys.exit(1)


def batch_process(args):
    """Process multiple locations from file."""
    config = load_config(args.config)
    
    if not os.path.exists(args.file):
        print(f"Error: File {args.file} not found")
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
                    print(f"Warning: Invalid format at line {line_num}: {line}")
            except ValueError as e:
                print(f"Warning: Error parsing line {line_num}: {e}")
    
    if not locations:
        print("No valid locations found in file")
        sys.exit(1)
    
    # Process each location
    style_name = args.style or config['default']['style']
    style = config['styles'].get(style_name, config['styles']['minimal'])
    dpi = args.dpi or config['default']['dpi']
    
    print(f"Processing {len(locations)} locations...")
    
    for i, loc in enumerate(locations, 1):
        print(f"[{i}/{len(locations)}] Creating map for {loc['name']}...")
        
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
                print(f"  Saved: {output_path}")
            else:
                print(f"  Error: Could not create map for {loc['name']}")
                
        except Exception as e:
            print(f"  Error processing {loc['name']}: {e}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description='Umap - Create beautiful maps from OpenStreetMap data')
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
    
    if args.command == 'create':
        create_map(args)
    elif args.command == 'batch':
        batch_process(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main() 