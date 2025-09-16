# Umap

Create beautiful maps from OpenStreetMap data with Python.

## Features

- **Simple CLI:** Just type `umap Istanbul` and get your map!
- **Auto Caching:** Fast map generation for repeated areas
- **Smart Optimization:** Automatic detail adjustment based on radius
- **Multiple Styles:** minimal, blueprint, vintage styles included
- **Python API:** Full programmatic control

## Installation

```bash
pip install umap-osm
```

## Usage

```bash
# Simple usage
umap Istanbul
umap "New York"

# With coordinates
umap --coords "40.66,29.28"

# Custom options
umap Istanbul --style vintage --radius 10000
```

## Python API

```python
import umap

# Create and save a map
plot = umap.plot((40.66, 29.28), radius=5000, style='vintage')
if plot.fig:
    umap.add_frame(plot.ax)
    plot.fig.savefig('map.png', dpi=300, bbox_inches='tight')
```

## New Update

- CLI now respects YAML config defaults (radius, style, format, cache) instead of overriding them
- `plot` accepts shared `fig`/`ax`, so `multiplot` truly renders on a single canvas
- Background style dictionaries stay intact across runs, giving consistent layering
- Legend label for 'K\u00f6pr\u00fcler' uses ASCII escapes to avoid encoding glitches

## Styles

- `minimal`: Clean black & white
- `blueprint`: Technical drawing look  
- `vintage`: Retro map style

## License

MIT License
