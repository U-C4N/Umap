"""Example script demonstrating Umap usage with Yalova, Turkey."""
import umap

# Create a map of central Yalova
plot = umap.plot(
    (40.66, 29.28),  # Moved north to show more of Marmara Sea
    radius=5000,  # 5km radius to include coastline
    layers={
        'perimeter': {},
        'streets': {
            'width': {
                'motorway': 5,
                'trunk': 5,
                'primary': 4.5,
                'secondary': 4,
                'tertiary': 3.5,
                'residential': 3,
                'service': 2,
                'footway': 1
            }
        },
        'building': {
            'tags': {'building': True}
        },
        'water': {
            'tags': {
                'natural': ['water', 'bay'],
                'place': 'sea',
                'water': 'sea'
            }
        },
        'coastline': {
            'tags': {'natural': 'coastline'}
        },
        'forest': {
            'tags': {'landuse': 'forest'}
        },
        'green': {
            'tags': {
                'landuse': ['grass', 'orchard'],
                'natural': ['island', 'wood'],
                'leisure': 'park'
            }
        }
    },
    style={
        'perimeter': {
            'fill': False,
            'lw': 0,
            'zorder': 0
        },
        'background': {
            'fc': '#F2F4CB',
            'zorder': -1
        },
        'green': {
            'fc': '#8BB174',
            'ec': '#2F3737',
            'hatch_c': '#A7C497',
            'hatch': 'ooo...',
            'lw': 1,
            'zorder': 1
        },
        'forest': {
            'fc': '#64B96A',
            'ec': '#2F3737',
            'lw': 1,
            'zorder': 2
        },
        'coastline': {
            'ec': '#2F3737',
            'lw': 1,
            'zorder': 2
        },
        'water': {
            'fc': '#a8e1e6',
            'ec': '#2F3737',
            'hatch_c': '#9bc3d4',
            'hatch': 'ooo...',
            'lw': 1,
            'zorder': 3
        },
        'streets': {
            'fc': '#2F3737',
            'ec': '#475657',
            'alpha': 1,
            'lw': 0,
            'zorder': 4
        },
        'building': {
            'palette': ['#433633', '#FF5E5B'],
            'ec': '#2F3737',
            'lw': 0.5,
            'zorder': 5
        }
    },
    circle=False,  # Square boundary
    dilate=None,  # No dilation needed for minimal style
    figsize=(12, 12),
    mode="matplotlib"  # Ensure we're in matplotlib mode
)

# Add frame and save
if plot.fig and plot.ax:
    # Add minimalist frame
    umap.add_frame(plot.ax)
    
    # Add padding
    plot.fig.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)
    
    # Save with high DPI for crisp lines
    plot.fig.savefig('examples/yalova_map.png', dpi=600, bbox_inches='tight', 
                     facecolor='#fff', pad_inches=0.5)
