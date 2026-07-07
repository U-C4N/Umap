"""Predefined styles for Umap."""
from typing import Dict, Any

# Predefined styles
# Each style has 'sea' (ocean/background color) and 'land' (filled perimeter color)
# so that coastal areas render correctly: sea is drawn first, then land on top.
STYLES: Dict[str, Dict[str, Any]] = {
    'minimal': {
        'perimeter': {'fill': False, 'lw': 0, 'zorder': 0},
        'sea':  {'fc': '#dbeafe', 'ec': 'none', 'zorder': -2},
        'land': {'fc': '#ffffff', 'ec': 'none', 'zorder': -1},
        'background': {'fc': '#dbeafe', 'zorder': -2, 'pad': 1.02},
        'green': {'fc': '#d3e6d3', 'ec': '#b7d4b7', 'lw': 0.2, 'zorder': 1},
        'streets': {
            'ec': '#334155', 'lw': 0.5, 'zorder': 4,
            'casing_ec': '#94a3b8', 'casing_alpha': 0.4, 'casing_scale': 1.4
        },
        'bridges': {'ec': '#dc2626', 'lw': 1.0, 'zorder': 6, 'alpha': 0.9},
        'building': {'ec': '#94a3b8', 'fc': '#f1f5f9', 'lw': 0.3, 'zorder': 5},
        'water': {'ec': '#60a5fa', 'fc': '#bfdbfe', 'lw': 0.3, 'zorder': 2},
        'waterway': {'ec': '#3b82f6', 'lw': 0.8, 'alpha': 0.85, 'zorder': 3}
    },
    'blueprint': {
        'perimeter': {'fill': False, 'lw': 0, 'zorder': 0},
        'sea':  {'fc': '#020617', 'ec': 'none', 'zorder': -2},
        'land': {'fc': '#0f172a', 'ec': 'none', 'zorder': -1},
        'background': {'fc': '#020617', 'zorder': -2, 'pad': 1.02},
        'green': {'fc': '#122e26', 'ec': '#1d4a3c', 'lw': 0.3, 'zorder': 1, 'alpha': 0.9},
        'streets': {
            'ec': '#e2e8f0', 'lw': 1.0, 'zorder': 4,
            'casing_ec': '#1e293b', 'casing_alpha': 0.8, 'casing_scale': 1.8
        },
        'bridges': {'ec': '#fbbf24', 'lw': 1.4, 'zorder': 6, 'alpha': 0.9},
        'building': {'ec': '#475569', 'fc': '#1e293b', 'lw': 0.5, 'zorder': 5, 'alpha': 0.85},
        'water': {'ec': '#38bdf8', 'fc': '#1e3a5f', 'lw': 0.4, 'zorder': 2, 'alpha': 0.9},
        'waterway': {'ec': '#38bdf8', 'lw': 0.9, 'alpha': 0.9, 'zorder': 3}
    },
    'vintage': {
        'perimeter': {'fill': False, 'lw': 0, 'zorder': 0},
        'sea':  {'fc': '#b0c4de', 'ec': 'none', 'zorder': -2},
        'land': {'fc': '#faf0e6', 'ec': 'none', 'zorder': -1},
        'background': {'fc': '#b0c4de', 'zorder': -2, 'pad': 1.02},
        'green': {'fc': '#cdd9a5', 'ec': '#adbd80', 'lw': 0.3, 'zorder': 1},
        'streets': {
            'ec': '#8b4513', 'lw': 0.5, 'zorder': 4,
            'casing_ec': '#d2b48c', 'casing_alpha': 0.5, 'casing_scale': 1.6
        },
        'bridges': {'ec': '#a0522d', 'lw': 1.2, 'zorder': 6, 'alpha': 0.9},
        'building': {'ec': '#a0845c', 'fc': '#f5deb3', 'lw': 0.3, 'zorder': 5},
        'water': {'ec': '#4682b4', 'fc': '#87ceeb', 'lw': 0.4, 'zorder': 2},
        'waterway': {'ec': '#5f9ea0', 'lw': 0.8, 'alpha': 0.85, 'zorder': 3}
    },
    # Dark city at night: streets rendered with a multi-pass neon glow.
    'neon': {
        'perimeter': {'fill': False, 'lw': 0, 'zorder': 0},
        'sea':  {'fc': '#04040c', 'ec': 'none', 'zorder': -2},
        'land': {'fc': '#0a0a16', 'ec': 'none', 'zorder': -1},
        'background': {'fc': '#04040c', 'zorder': -2, 'pad': 1.02},
        'green': {'fc': '#0a1f14', 'ec': '#0f3320', 'lw': 0.3, 'zorder': 1},
        'streets': {
            'ec': '#00e5ff', 'lw': 0.7, 'zorder': 4,
            'glow': True, 'glow_scale': 7.0, 'glow_alpha': 0.055
        },
        'bridges': {
            'ec': '#ff2d95', 'lw': 1.1, 'zorder': 6, 'alpha': 0.95,
            'glow': True, 'glow_color': '#ff2d95', 'glow_scale': 5.0, 'glow_alpha': 0.06
        },
        'building': {
            'ec': '#b366ff', 'fc': '#12081f', 'lw': 0.35, 'zorder': 5,
            'glow': True, 'glow_scale': 4.0, 'glow_alpha': 0.045
        },
        'water': {'ec': '#00b3ff', 'fc': '#02121f', 'lw': 0.5, 'zorder': 2, 'alpha': 0.95},
        'waterway': {
            'ec': '#00b3ff', 'lw': 0.9, 'alpha': 0.9, 'zorder': 3,
            'glow': True, 'glow_scale': 4.0, 'glow_alpha': 0.05
        }
    },
    # 2.5D isometric paper-model look: buildings extruded by their
    # OSM 'building:levels' / 'height' tags with shaded walls and soft shadows.
    'papercraft': {
        'perimeter': {'fill': False, 'lw': 0, 'zorder': 0},
        'sea':  {'fc': '#bcd7e0', 'ec': 'none', 'zorder': -2},
        'land': {'fc': '#f4efe4', 'ec': 'none', 'zorder': -1},
        'background': {'fc': '#bcd7e0', 'zorder': -2, 'pad': 1.02},
        'green': {'fc': '#d9e3c5', 'ec': '#c3d1a6', 'lw': 0.25, 'zorder': 1},
        'streets': {'ec': '#d8cfbd', 'lw': 1.1, 'zorder': 3},
        'bridges': {'ec': '#c9b79b', 'lw': 1.4, 'zorder': 3.5, 'alpha': 0.9},
        'water': {'ec': '#8fb8c9', 'fc': '#a9cddd', 'lw': 0.4, 'zorder': 2},
        'waterway': {'ec': '#8fb8c9', 'lw': 0.8, 'alpha': 0.85, 'zorder': 2.5},
        'building': {
            'zorder': 5,
            'extrude': {
                'direction': 62,          # extrusion azimuth in degrees (from +x axis)
                'scale': 0.0018,          # per-level height as fraction of map span
                'default_levels': 2,
                'wall_fc': '#d9cfba',
                'roof_fc': '#fffdf7',
                'roof_ec': '#c4b89e',
                'roof_lw': 0.25,
                'shadow_fc': '#8a8577',
                'shadow_alpha': 0.18
            }
        }
    }
}

def get_style(style_name: str) -> Dict[str, Any]:
    """Get a predefined style by name.
    
    Args:
        style_name: Name of the style ('minimal', 'blueprint', 'vintage')
        
    Returns:
        Style dictionary
        
    Raises:
        KeyError: If style_name is not found
    """
    if style_name not in STYLES:
        raise KeyError(f"Style '{style_name}' not found. Available styles: {list(STYLES.keys())}")
    
    return STYLES[style_name].copy()

def list_styles() -> list:
    """List all available predefined styles."""
    return list(STYLES.keys())

def register_style(name: str, style: Dict[str, Any]) -> None:
    """Register a new custom style.
    
    Args:
        name: Name for the new style
        style: Style dictionary
    """
    STYLES[name] = style.copy()
