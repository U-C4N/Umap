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
        'streets': {
            'ec': '#8b4513', 'lw': 0.5, 'zorder': 4,
            'casing_ec': '#d2b48c', 'casing_alpha': 0.5, 'casing_scale': 1.6
        },
        'bridges': {'ec': '#a0522d', 'lw': 1.2, 'zorder': 6, 'alpha': 0.9},
        'building': {'ec': '#a0845c', 'fc': '#f5deb3', 'lw': 0.3, 'zorder': 5},
        'water': {'ec': '#4682b4', 'fc': '#87ceeb', 'lw': 0.4, 'zorder': 2},
        'waterway': {'ec': '#5f9ea0', 'lw': 0.8, 'alpha': 0.85, 'zorder': 3}
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
