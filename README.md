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

## Styles

- `minimal`: Clean black & white
- `blueprint`: Technical drawing look  
- `vintage`: Retro map style

## License

MIT License
