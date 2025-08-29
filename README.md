# Umap v3.0

A powerful Python library for creating beautiful, customized maps from OpenStreetMap data. Now with **simplified CLI**, **automatic caching**, and **smart optimization**!

![Yalova CLI Minimal](yalova_minimal.png)
*Minimal style map of Yalova created with CLI*

## 🚀 Key Features

- **🔧 Super Simple CLI:** Just type `umap Istanbul` and get your map on desktop!
- **🖥️ Desktop Output:** Maps automatically saved to your desktop
- **💾 Automatic Caching:** Speeds up repeated map generation for the same area
- **⚡ Auto Optimization:** Intelligently adjusts map details based on the requested radius
- **🎨 Enhanced Styles:** Includes `minimal`, `blueprint`, and `vintage` styles out-of-the-box
- **🔄 Batch Processing:** Generate multiple maps from a list of locations
- **🐍 Python API:** Full programmatic control for advanced customization

## Umap v3 Highlights

- **✨ Streamlined CLI:** No complex subcommands - just `umap <city>` and done!
- **📦 PyPI Packaging:** Easy installation and direct command access
- **🔖 Version Constant:** Access the library version with `umap.__version__`
- **🔇 Clean Output:** No verbose logging, just clear progress messages

## Installation

```bash
# Install from PyPI
pip install umap-osm

# For developers
git clone https://github.com/U-C4N/Umap.git
cd Umap
pip install -e .
```

## 🔧 CLI Quick Start

**Super simple - just name your location:**

```bash
# After pip install, use direct commands
umap Istanbul
umap "New York"
umap London

# Or without pip install
python umap Istanbul
python umap Ankara
python umap "Los Angeles"

# With coordinates
umap --coords "40.66,29.28"

# Custom options
umap Istanbul --style vintage --radius 10000 --format pdf
```

![Yalova CLI Blueprint](yalova_cli_test.png)
*Blueprint style map of Yalova created with CLI*

### CLI Options

```bash
umap --help              # See all options
umap Istanbul --style blueprint --radius 8000 --format svg
umap "New York" --output "/path/to/my/map.jpg" --format jpg
umap --coords "40.66,29.28" --style vintage --format png
```

**All maps are automatically saved to your Desktop unless you specify `--output`**

### 🔧 Troubleshooting

If `umap` command is not found after installation:

**Windows:**
```bash
# Use Python module approach
python -m umap Istanbul

# Or add Python Scripts to PATH:
# Add C:\Users\YourUser\AppData\Roaming\Python\Python3xx\Scripts to PATH
```

**macOS/Linux:**
```bash
# Use Python module approach  
python -m umap Istanbul

# Or check PATH includes pip install location
pip show -v umap-osm
```

## 📚 Python API Example

```python
import umap

# Create and save a map
plot = umap.plot(
    (40.66, 29.28),  # Yalova coordinates
    radius=5000,
    style='vintage'  # Use a predefined style name or a custom style dict
)

if plot.fig:
    umap.add_frame(plot.ax) # Optional: Add a frame
    plot.fig.savefig('yalova_api_vintage.png', dpi=300, bbox_inches='tight')
```

![Yalova API Vintage](yalova_vintage.png)
*Vintage style map of Yalova created with Python API*

## 🎨 Styles

Umap comes with several built-in styles:
- `minimal`: Clean black & white.
- `blueprint`: Technical drawing look.
- `vintage`: Retro, old-map feel.

You can also define your own custom styles. See `umap/cli.py` for examples of style dictionaries.

## 💾 Caching & Optimization

- **Caching:** Data downloaded from OpenStreetMap is automatically cached in `~/.umap_cache` to speed up subsequent runs for the same area.
- **Optimization:** Map details (like road types shown or minimum building size) are automatically adjusted based on the map's radius for better performance and visual clarity.

## 🧪 Examples & Testing

Check the `examples/` directory:
- `yalova_styles.py`: Generates maps of Yalova in all predefined styles.
- `yalova_performance.py`: Benchmarks map generation for different radii.

Run them from the project root:
```bash
python examples/yalova_styles.py
python examples/yalova_performance.py
```

## 🔧 Development

Key modules:
- `umap/core/plot.py`: Core plotting logic.
- `umap/core/fetch.py`: Data fetching from OSM.
- `umap/cli.py`: Command Line Interface.
- `umap/utils/cache.py`: Caching mechanism.
- `umap/utils/optimization.py`: Performance and detail optimization.

## License
MIT License

## Author

<p align="left">
<b>Umutcan Edizaslan:</b>
<a href="https://github.com/U-C4N" target="blank"><img align="center" src="https://raw.githubusercontent.com/tandpfun/skill-icons/main/icons/Github-Dark.svg" alt="Umutcan Edizaslan GitHub" height="30" width="40" /></a>
<a href="https://x.com/UEdizaslan" target="blank"><img align="center" src="https://raw.githubusercontent.com/tandpfun/skill-icons/main/icons/Twitter.svg" alt="Umutcan Edizaslan Twitter" height="30" width="40" /></a>
<a href="https://discord.gg/2Tutcj6u" target="blank"><img align="center" src="https://raw.githubusercontent.com/tandpfun/skill-icons/main/icons/Discord.svg" alt="Umutcan Edizaslan Discord" height="30" width="40" /></a>
</p>

---

**Umap v3.0** - Making beautiful maps easier than ever! 🗺️
