# Installation Guide

## Requirements
- Python 3.8 or higher
- pip package manager

## Dependencies
- OSMnx: For fetching OpenStreetMap data
- Matplotlib: For visualization
- Shapely: For geometric operations
- vsketch (optional): For pen plotter support

## Installation Steps

### 1. Simple Installation
```bash
pip install umap-osm
```

### 2. Development Installation
For contributing or local development:
```bash
git clone https://github.com/U-C4N/Umap.git
cd Umap
pip install -e .
```

### 3. Verify Installation
```python
import umap

# Create a simple test map
plot = umap.plot(
    (40.66, 29.28),
    radius=1000
)
```

If you see no errors, the installation was successful.
```

### 4. Check Version
```python
import umap
print(umap.__version__)  # Should print the current version
```

## Common Issues

### Missing Dependencies
If you encounter missing dependency errors, install them manually:
```bash
pip install osmnx matplotlib shapely
```

### Optional Dependencies
For pen plotter support:
```bash
pip install git+https://github.com/abey79/vsketch@1.0.0
```
