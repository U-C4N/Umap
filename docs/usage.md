# Umap Usage Guide / Umap Kullanım Kılavuzu

## English

### Basic Usage
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

### Customization
You can customize the map by providing layers and style configurations:

```python
plot = umap.plot(
    (40.66, 29.28),
    layers={
        'perimeter': {},
        'streets': {
            'width': {
                'primary': 4,
                'secondary': 3,
                'tertiary': 2,
                'residential': 2
            }
        },
        'building': {'tags': {'building': True}},
        'water': {
            'tags': {
                'natural': ['water', 'bay'],
                'place': 'sea',
                'water': 'sea'
            }
        },
        'coastline': {'tags': {'natural': 'coastline'}},
        'green': {'tags': {'landuse': ['grass', 'park'], 'leisure': 'park'}},
        'forest': {'tags': {'landuse': 'forest'}}
    },
    style={
        'perimeter': {'fill': False, 'lw': 0},
        'streets': {'ec': '#2F3737', 'lw': 0.5},
        'building': {'palette': ['#433633', '#FF5E5B'], 'ec': '#2F3737', 'lw': 0.5},
        'water': {'fc': '#a8e1e6', 'ec': '#2F3737', 'lw': 1},
        'green': {'fc': '#8BB174', 'ec': '#2F3737', 'lw': 1},
        'forest': {'fc': '#64B96A', 'ec': '#2F3737', 'lw': 1}
    }
)
```

### Default Style
When no style is provided, Umap uses a minimalist black and white style:
- Black lines (#000)
- White background and fills (#fff)
- Clean line weights (0.5px)
- Simple layer set (perimeter, streets, building)

## Türkçe

### Temel Kullanım
```python
import umap

# Sadece koordinat ve yarıçap ile minimal harita oluşturma
plot = umap.plot(
    (40.66, 29.28),  # Koordinatlar (enlem, boylam)
    radius=5000,     # Yarıçap (metre cinsinden)
)

# Haritayı kaydetme
plot.fig.savefig('harita.jpg', dpi=600, bbox_inches='tight')
```

### Özelleştirme
Katmanları ve stil yapılandırmalarını sağlayarak haritayı özelleştirebilirsiniz:

```python
plot = umap.plot(
    (40.66, 29.28),
    layers={
        'perimeter': {},
        'streets': {
            'width': {
                'primary': 4,
                'secondary': 3,
                'tertiary': 2,
                'residential': 2
            }
        },
        'building': {'tags': {'building': True}},
        'water': {
            'tags': {
                'natural': ['water', 'bay'],
                'place': 'sea',
                'water': 'sea'
            }
        },
        'coastline': {'tags': {'natural': 'coastline'}},
        'green': {'tags': {'landuse': ['grass', 'park'], 'leisure': 'park'}},
        'forest': {'tags': {'landuse': 'forest'}}
    },
    style={
        'perimeter': {'fill': False, 'lw': 0},
        'streets': {'ec': '#2F3737', 'lw': 0.5},
        'building': {'palette': ['#433633', '#FF5E5B'], 'ec': '#2F3737', 'lw': 0.5},
        'water': {'fc': '#a8e1e6', 'ec': '#2F3737', 'lw': 1},
        'green': {'fc': '#8BB174', 'ec': '#2F3737', 'lw': 1},
        'forest': {'fc': '#64B96A', 'ec': '#2F3737', 'lw': 1}
    }
)
```

### Varsayılan Stil
Herhangi bir stil belirtilmediğinde, Umap minimalist siyah-beyaz bir stil kullanır:
- Siyah çizgiler (#000)
- Beyaz arka plan ve dolgular (#fff)
- Temiz çizgi kalınlıkları (0.5px)
- Basit katman seti (çevre, sokaklar, binalar)
