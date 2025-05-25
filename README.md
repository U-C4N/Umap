# Umap v2.0

A powerful Python library for creating beautiful, customized maps from OpenStreetMap data. Now with **CLI support**, **automatic caching**, and **smart optimization**!

## 🚀 What's New in v2.0

- **🔧 Command Line Interface (CLI)** - Create maps directly from terminal
- **💾 Automatic Caching** - Smart data caching for faster repeated operations
- **⚡ Auto Optimization** - Intelligent layer optimization based on map size
- **🎨 Enhanced Styles** - New blueprint and vintage styles
- **📊 Performance Tools** - Built-in benchmarking and profiling
- **🔄 Batch Processing** - Process multiple locations at once

## Features

- Create minimalist black and white maps with just coordinates and radius
- Draw customized maps from OpenStreetMap data with rich styling options
- Support for multiple map layers (buildings, streets, water bodies, etc.)
- High DPI output for crisp, clean lines
- Support for multiple map views with multiplot functionality
- Optional pen plotter support via vsketch
- **NEW:** Terminal-based CLI for quick map generation
- **NEW:** Automatic data caching system
- **NEW:** Smart performance optimization

## Installation

```bash
pip install umap-osm
```

For development:
```bash
git clone https://github.com/U-C4N/Umap.git
cd Umap
pip install -r requirements.txt
```

## 🔧 CLI Usage (New!)

### Quick Start with CLI
```bash
# Create a map with coordinates
python -m umap create --coords "40.66,29.28" --radius 5000 --output yalova.png

# Create a map with address
python -m umap create --address "Yalova, Turkey" --radius 3000 --style blueprint

# Use different styles
python -m umap create --coords "40.66,29.28" --style vintage --dpi 600
```

### Available Styles
- **minimal** - Clean black and white (default)
- **blueprint** - Technical blue style
- **vintage** - Retro brown/beige style

### CLI Commands

#### Single Map Creation
```bash
python -m umap create [OPTIONS]

Options:
  --coords "lat,lon"     Coordinates (e.g., "40.66,29.28")
  --address "location"   Address or place name
  --radius METERS        Radius in meters (default: 5000)
  --style STYLE          Style name (minimal/blueprint/vintage)
  --output PATH          Output file path
  --dpi DPI              Image DPI (default: 300)
  --config PATH          Custom config file path
```

#### Batch Processing
```bash
python -m umap batch --file locations.txt --style blueprint

Options:
  --file PATH            File with locations (required)
  --style STYLE          Style for all maps
  --format FORMAT        Output format (png/jpg)
  --dpi DPI              Image DPI
```

**Batch file format (locations.txt):**
```
# name,latitude,longitude,radius
yalova,40.66,29.28,5000
istanbul,41.01,28.97,10000
ankara,39.92,32.85,8000
```

### CLI Examples
```bash
# High-resolution blueprint style
python -m umap create --coords "40.66,29.28" --radius 3000 --style blueprint --dpi 600 --output yalova_hq.png

# Vintage style with custom radius
python -m umap create --address "Istanbul, Turkey" --radius 15000 --style vintage

# Batch process multiple cities
python -m umap batch --file cities.txt --style minimal --dpi 300
```

## 📚 Python API Usage

### Quick Start
```python
import umap

# Create a minimal map with just coordinates and radius
plot = umap.plot(
    (40.66, 29.28),  # Coordinates (latitude, longitude)
    radius=5000,     # Radius in meters
)

# Save the map
plot.fig.savefig('map.jpg', dpi=600, bbox_inches='tight')
```

### Advanced Usage with Styles
```python
import umap

# Create a blueprint style map
plot = umap.plot(
    (40.66, 29.28),
    radius=5000,
    style={
        'perimeter': {'fill': False, 'lw': 0, 'zorder': 0},
        'background': {'fc': '#1e3a8a', 'zorder': -1},
        'streets': {'ec': '#fff', 'lw': 0.8, 'zorder': 4},
        'building': {'ec': '#fff', 'fc': 'none', 'lw': 0.6, 'zorder': 5},
        'water': {'ec': '#3b82f6', 'fc': '#3b82f6', 'lw': 0.5, 'zorder': 3}
    }
)

# Add frame and save
umap.add_frame(plot.ax)
plot.fig.savefig('blueprint_map.png', dpi=600, bbox_inches='tight')
```

### Customized Colorful Map
```python
# examples/yalova_map.py
plot = umap.plot(
    (40.66, 29.28),
    layers={
        'water': {'tags': {'natural': ['water', 'bay']}},
        'green': {'tags': {'landuse': ['grass', 'park']}},
        'building': {'tags': {'building': True}}
    },
    style={
        'water': {'fc': '#a8e1e6', 'ec': '#2F3737'},
        'green': {'fc': '#8BB174', 'ec': '#2F3737'},
        'building': {'palette': ['#433633', '#FF5E5B']}
    }
)
```

## 💾 Caching System (New!)

Umap v2.0 automatically caches downloaded data for faster repeated operations:

```python
# First run: Downloads data from OpenStreetMap
plot1 = umap.plot((40.66, 29.28), radius=5000)

# Second run: Uses cached data (much faster!)
plot2 = umap.plot((40.66, 29.28), radius=5000)
```

**Cache management:**
```python
import umap.utils.cache as cache

# Get cache info
info = cache.get_cache_info()
print(f"Cache size: {info['total_size_mb']:.1f}MB")

# Clear old cache files (older than 3 days)
removed = cache.clear_cache(older_than_days=3)
print(f"Removed {removed} cache files")
```

## ⚡ Performance Optimization (New!)

Automatic optimization based on map radius:

- **Small areas (< 1km):** High detail, includes footways
- **Medium areas (1-5km):** Medium detail, major roads only
- **Large areas (5-15km):** Low detail, filters small buildings
- **Very large areas (> 15km):** Minimal detail, highways only

```python
# Optimization is automatic, but you can check stats
from umap.utils.optimization import get_processing_stats

plot = umap.plot((40.66, 29.28), radius=10000)
stats = get_processing_stats(plot.geodataframes)
print(f"Buildings: {stats['building']['feature_count']}")
```

## 🧪 Testing and Benchmarking

### Style Testing
```bash
# Test all styles with Yalova coordinates
python examples/yalova_styles.py
```

### Performance Testing
```bash
# Benchmark different radius values
python examples/yalova_performance.py
```

## 📁 Configuration

Create `~/.umap/config.yaml` for custom defaults:

```yaml
default:
  style: minimal
  dpi: 300
  format: png
  cache_enabled: true
  radius: 5000

styles:
  custom_dark:
    background: "#2d3748"
    streets: "#e2e8f0"
    buildings: "#4a5568"
    water: "#2b6cb0"
```

## Examples

### Minimal Black and White Map
![Minimal Style](examples/example2.jpg)
```bash
python -m umap create --coords "40.66,29.28" --style minimal
```

### Blueprint Technical Style
```bash
python -m umap create --coords "40.66,29.28" --style blueprint --output blueprint.png
```

### Vintage Style Map
```bash
python -m umap create --coords "40.66,29.28" --style vintage --radius 3000
```

### Batch Processing Example
```bash
# Create locations.txt file:
# yalova,40.66,29.28,5000
# istanbul,41.01,28.97,10000

python -m umap batch --file locations.txt --style blueprint
```

## Default Style
When no style is provided, Umap uses a minimalist black and white style:
- Black lines (#000)
- White background and fills (#fff)
- Clean line weights (0.5px)
- Simple layer set (perimeter, streets, building)

## 🔧 Development

### Requirements
- Python 3.8+
- geopandas
- matplotlib
- osmnx
- psutil
- PyYAML

### Running Tests
```bash
# Install dependencies
pip install -r requirements.txt

# Run style tests
python examples/yalova_styles.py

# Run performance tests
python examples/yalova_performance.py

# Test CLI
python -m umap create --coords "40.66,29.28" --radius 5000
```

## 📈 Performance Tips

1. **Use caching:** Repeated operations on same location are much faster
2. **Optimize radius:** Larger radius = longer processing time
3. **Choose appropriate style:** Complex styles take more time to render
4. **Batch processing:** More efficient for multiple locations

## License
MIT License

## Author

<p align="left">
<b>Umutcan Edizaslan:</b>
<a href="https://github.com/U-C4N" target="blank"><img align="center" src="https://raw.githubusercontent.com/tandpfun/skill-icons/main/icons/Github-Dark.svg" alt="TutTrue" height="30" width="40" /></a>
<a href="https://x.com/UEdizaslan" target="blank"><img align="center" src="https://raw.githubusercontent.com/tandpfun/skill-icons/main/icons/Twitter.svg" height="30" width="40" /></a>
<a href="https://discord.gg/2Tutcj6u" target="blank"><img align="center" src="https://raw.githubusercontent.com/tandpfun/skill-icons/main/icons/Discord.svg" height="30" width="40" /></a>
</p>

---

## 🚀 What's Coming Next

- SVG and PDF export support
- Interactive web interface
- More preset styles
- Advanced filtering options
- Plugin system

**Umap v2.0** - Making beautiful maps easier than ever! 🗺️
