"""Test different styles with Yalova location."""
import umap
import time

# Test coordinates for Yalova
YALOVA_COORDS = (40.66, 29.28)
RADIUS = 5000

# Define styles to test
styles = {
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

def test_style(style_name, style_config):
    """Test a single style and save the result."""
    print(f"\nTesting {style_name} style...")
    start_time = time.time()
    
    try:
        # Create plot with style
        plot = umap.plot(
            YALOVA_COORDS,
            radius=RADIUS,
            style=style_config,
            figsize=(12, 12)
        )
        
        if plot.fig and plot.ax:
            # Add frame
            umap.add_frame(plot.ax)
            
            # Save with style name
            output_path = f'examples/yalova_{style_name}.png'
            plot.fig.savefig(
                output_path,
                dpi=600,
                bbox_inches='tight',
                facecolor='#fff',
                pad_inches=0.5
            )
            
            end_time = time.time()
            print(f"✓ {style_name} style completed in {end_time - start_time:.2f}s")
            print(f"  Saved: {output_path}")
            
        else:
            print(f"✗ Failed to create {style_name} style")
            
    except Exception as e:
        print(f"✗ Error with {style_name} style: {e}")

def main():
    """Test all styles."""
    print("Testing different styles with Yalova coordinates...")
    print(f"Location: {YALOVA_COORDS}")
    print(f"Radius: {RADIUS}m")
    
    total_start = time.time()
    
    for style_name, style_config in styles.items():
        test_style(style_name, style_config)
    
    total_end = time.time()
    print(f"\nAll styles completed in {total_end - total_start:.2f}s")
    print(f"Generated {len(styles)} maps in examples/ directory")

if __name__ == "__main__":
    main() 