"""Drawing utilities for Umap."""
from matplotlib.patches import Rectangle

def add_frame(ax, linewidth: float = 0.5) -> None:
    """Add a minimalist frame to the plot."""
    if ax is None:
        return
        
    # Clear existing frame
    ax.set_frame_on(False)
    
    # Create frame
    ax.add_patch(Rectangle(
        (0, 0), 1, 1, transform=ax.transAxes,
        fill=False, color='black', linewidth=linewidth,
        clip_on=False
    ))
