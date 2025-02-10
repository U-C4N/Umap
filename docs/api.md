# API Reference

## Core Functions

### plot()
Create a map from OpenStreetMap data.

```python
umap.plot(
    query: Union[str, Tuple[float, float], GeoDataFrame],
    layers: Optional[Dict] = None,
    style: Optional[Dict] = None,
    preset: str = "default",
    circle: Optional[bool] = None,
    radius: Optional[float] = None,
    dilate: Optional[float] = None,
    figsize: Tuple[int, int] = (12, 12),
    mode: str = "matplotlib",
    **kwargs
) -> Plot
```

#### Parameters
- `query`: Location query (coordinates, name, or OSM ID)
- `layers`: Dictionary of layer configurations
- `style`: Dictionary of style configurations
- `preset`: Style preset name
- `circle`: Use circular boundary if True
- `radius`: Boundary radius in meters
- `dilate`: Dilation amount for perimeter
- `figsize`: Figure size in inches
- `mode`: Rendering mode ('matplotlib' or 'plotter')

#### Returns
- `Plot` object containing the map figure and data

### multiplot()
Create multiple maps on the same canvas.

```python
umap.multiplot(
    *subplots: Subplot,
    figsize: Tuple[int, int] = (12, 12),
    **kwargs
) -> List[Plot]
```

#### Parameters
- `*subplots`: Subplot objects defining each map
- `figsize`: Figure size in inches
- `**kwargs`: Additional arguments passed to plot()

#### Returns
- List of Plot objects

## Classes

### Plot
Container for map data and figure.

#### Attributes
- `geodataframes`: Dictionary of GeoDataFrames
- `fig`: Matplotlib figure
- `ax`: Matplotlib axes
- `background`: Background geometry

### Subplot
Class for organizing multiple map views.

#### Attributes
- `query`: Location query
- `kwargs`: Plot parameters

## Layer Configuration

### Available Layers
- `perimeter`: Map boundary
- `streets`: Street network
- `building`: Building footprints
- `water`: Water bodies
- `coastline`: Coastline features
- `green`: Green spaces
- `forest`: Forest areas

### Layer Parameters
```python
{
    'tags': dict,     # OSM tags to fetch
    'width': dict,    # Line widths for streets
    'custom_filter': str,  # Custom OSM filter
    'union': bool     # Union geometries
}
```

## Style Configuration

### Style Parameters
```python
{
    'fc': str,        # Fill color
    'ec': str,        # Edge color
    'lw': float,      # Line width
    'alpha': float,   # Transparency
    'zorder': int,    # Layer order
    'hatch': str,     # Hatch pattern
    'hatch_c': str,   # Hatch color
    'palette': list   # Color palette
}
```

### Default Style
When no style is provided:
```python
{
    'perimeter': {'fill': False, 'lw': 0, 'zorder': 0},
    'background': {'fc': '#fff', 'zorder': -1},
    'streets': {'ec': '#000', 'lw': 0.5, 'zorder': 4},
    'building': {'ec': '#000', 'fc': '#fff', 'lw': 0.5, 'zorder': 5}
}
```
