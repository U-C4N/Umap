"""Example script demonstrating minimal Umap usage with Yalova, Turkey."""
import umap

# Create a minimal map of Yalova
plot = umap.plot(
    (40.66, 29.28),  # Coordinates for Yalova
    radius=5000,     # 5km radius
)

# Add frame and save
if plot.fig and plot.ax:
    # Add minimalist frame
    umap.add_frame(plot.ax)
    
    # Save with high DPI for crisp lines
    plot.fig.savefig('examples/example2.jpg', dpi=600, bbox_inches='tight', 
                     facecolor='#fff', pad_inches=0.5)
