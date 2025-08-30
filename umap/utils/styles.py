"""Predefined styles for Umap."""
from typing import Dict, Any

# Predefined styles
STYLES: Dict[str, Dict[str, Any]] = {
    'minimal': {
        'perimeter': {'fill': False, 'lw': 0, 'zorder': 0},
        'background': {'fc': '#fff', 'zorder': -1},
        'streets': {
            'ec': '#0f172a', 'lw': 0.6, 'zorder': 4,
            'casing_ec': '#94a3b8', 'casing_alpha': 0.6, 'casing_scale': 1.8
        },
        'bridges': {'ec': '#ef4444', 'lw': 1.4, 'zorder': 6, 'alpha': 0.95},
        'building': {'ec': '#000', 'fc': '#fff', 'lw': 0.5, 'zorder': 5},
        'water': {'ec': '#3b82f6', 'fc': '#e0f2fe', 'lw': 0.2, 'zorder': 2},
        'waterway': {'ec': '#2563eb', 'lw': 0.9, 'alpha': 0.9, 'zorder': 3}
    },
    'blueprint': {
        'perimeter': {'fill': False, 'lw': 0, 'zorder': 0},
        'background': {'fc': '#0f172a', 'zorder': -1},
        'streets': {
            'ec': '#ffffff', 'lw': 1.2, 'zorder': 4,
            'casing_ec': '#1e293b', 'casing_alpha': 0.9, 'casing_scale': 2.2
        },
        'bridges': {'ec': '#fbbf24', 'lw': 1.6, 'zorder': 6, 'alpha': 0.95},
        'building': {'ec': '#ffffff', 'fc': '#1e293b', 'lw': 0.8, 'zorder': 5, 'alpha': 0.8},
        'water': {'ec': '#38bdf8', 'fc': '#1e40af', 'lw': 0.5, 'zorder': 2, 'alpha': 0.9},
        'waterway': {'ec': '#38bdf8', 'lw': 1.0, 'alpha': 0.95, 'zorder': 3}
    },
    'vintage': {
        'perimeter': {'fill': False, 'lw': 0, 'zorder': 0},
        'background': {'fc': '#f5f5dc', 'zorder': -1},
        'streets': {
            'ec': '#8b4513', 'lw': 0.6, 'zorder': 4,
            'casing_ec': '#d2b48c', 'casing_alpha': 0.8, 'casing_scale': 2.0
        },
        'bridges': {'ec': '#b45309', 'lw': 1.4, 'zorder': 6, 'alpha': 0.95},
        'building': {'ec': '#654321', 'fc': '#deb887', 'lw': 0.4, 'zorder': 5},
        'water': {'ec': '#4682b4', 'fc': '#87ceeb', 'lw': 0.5, 'zorder': 2},
        'waterway': {'ec': '#5f9ea0', 'lw': 0.9, 'alpha': 0.9, 'zorder': 3}
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
