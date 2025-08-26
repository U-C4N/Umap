"""Predefined styles for Umap."""
from typing import Dict, Any

# Predefined styles
STYLES: Dict[str, Dict[str, Any]] = {
    'minimal': {
        'perimeter': {'fill': False, 'lw': 0, 'zorder': 0},
        'background': {'fc': '#fff', 'zorder': -1},
        'streets': {'ec': '#000', 'lw': 0.5, 'zorder': 4},
        'building': {'ec': '#000', 'fc': '#fff', 'lw': 0.5, 'zorder': 5},
        'water': {'ec': '#000', 'fc': '#fff', 'lw': 0.5, 'zorder': 3}
    },
    'blueprint': {
        'perimeter': {'fill': False, 'lw': 0, 'zorder': 0},
        'background': {'fc': '#1e3a8a', 'zorder': -1},
        'streets': {'ec': '#fff', 'lw': 0.8, 'zorder': 4},
        'building': {'ec': '#fff', 'fc': 'none', 'lw': 0.6, 'zorder': 5},
        'water': {'ec': '#3b82f6', 'fc': '#3b82f6', 'lw': 0.5, 'zorder': 3}
    },
    'vintage': {
        'perimeter': {'fill': False, 'lw': 0, 'zorder': 0},
        'background': {'fc': '#f5f5dc', 'zorder': -1},
        'streets': {'ec': '#8b4513', 'lw': 0.6, 'zorder': 4},
        'building': {'ec': '#654321', 'fc': '#deb887', 'lw': 0.4, 'zorder': 5},
        'water': {'ec': '#4682b4', 'fc': '#87ceeb', 'lw': 0.5, 'zorder': 3}
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
