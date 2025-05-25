"""Performance testing with different radius values for Yalova."""
import umap
import time
import psutil
import os

# Test coordinates for Yalova
YALOVA_COORDS = (40.66, 29.28)

# Different radius values to test
TEST_RADII = [1000, 2500, 5000, 10000, 15000, 20000]

def get_memory_usage():
    """Get current memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def test_radius_performance(radius):
    """Test performance for a specific radius."""
    print(f"\nTesting radius: {radius}m")
    
    # Memory before
    memory_before = get_memory_usage()
    
    # Time the operation
    start_time = time.time()
    
    try:
        plot = umap.plot(
            YALOVA_COORDS,
            radius=radius,
            figsize=(12, 12)
        )
        
        # Memory after data fetch
        memory_after_fetch = get_memory_usage()
        
        if plot.fig and plot.ax:
            # Add frame and save
            umap.add_frame(plot.ax)
            
            output_path = f'examples/yalova_r{radius}.png'
            plot.fig.savefig(
                output_path,
                dpi=300,  # Lower DPI for performance testing
                bbox_inches='tight',
                facecolor='#fff',
                pad_inches=0.5
            )
            
            end_time = time.time()
            memory_after_render = get_memory_usage()
            
            # Calculate statistics
            total_time = end_time - start_time
            memory_used = memory_after_render - memory_before
            
            # Get feature counts if available
            feature_counts = {}
            if hasattr(plot, 'geodataframes'):
                for layer, gdf in plot.geodataframes.items():
                    feature_counts[layer] = len(gdf)
            
            print(f"✓ Radius {radius}m completed:")
            print(f"  Time: {total_time:.2f}s")
            print(f"  Memory used: {memory_used:.1f}MB")
            print(f"  Features: {feature_counts}")
            print(f"  Output: {output_path}")
            
            return {
                'radius': radius,
                'time': total_time,
                'memory_used': memory_used,
                'feature_counts': feature_counts,
                'success': True
            }
            
        else:
            print(f"✗ Failed to create map for radius {radius}m")
            return {
                'radius': radius,
                'success': False,
                'error': 'Failed to create plot'
            }
            
    except Exception as e:
        end_time = time.time()
        total_time = end_time - start_time
        print(f"✗ Error with radius {radius}m: {e}")
        return {
            'radius': radius,
            'time': total_time,
            'success': False,
            'error': str(e)
        }

def analyze_results(results):
    """Analyze and display performance results."""
    print("\n" + "="*60)
    print("PERFORMANCE ANALYSIS")
    print("="*60)
    
    successful_results = [r for r in results if r['success']]
    
    if not successful_results:
        print("No successful tests to analyze.")
        return
    
    print(f"{'Radius (m)':<10} {'Time (s)':<10} {'Memory (MB)':<12} {'Features':<10}")
    print("-" * 50)
    
    for result in successful_results:
        total_features = sum(result['feature_counts'].values()) if result['feature_counts'] else 0
        print(f"{result['radius']:<10} {result['time']:<10.2f} {result['memory_used']:<12.1f} {total_features:<10}")
    
    # Calculate trends
    if len(successful_results) > 1:
        print("\nTrends:")
        
        # Time vs radius
        times = [r['time'] for r in successful_results]
        radii = [r['radius'] for r in successful_results]
        
        time_per_radius = [(times[i] / radii[i]) * 1000 for i in range(len(times))]
        avg_time_per_1000m = sum(time_per_radius) / len(time_per_radius)
        
        print(f"Average time per 1000m radius: {avg_time_per_1000m:.3f}s")
        
        # Memory efficiency
        memories = [r['memory_used'] for r in successful_results]
        avg_memory = sum(memories) / len(memories)
        print(f"Average memory usage: {avg_memory:.1f}MB")
        
        # Feature density
        feature_counts = [sum(r['feature_counts'].values()) for r in successful_results if r['feature_counts']]
        if feature_counts:
            avg_features = sum(feature_counts) / len(feature_counts)
            print(f"Average feature count: {avg_features:.0f}")

def main():
    """Run performance tests."""
    print("Yalova Performance Testing")
    print(f"Location: {YALOVA_COORDS}")
    print(f"Testing {len(TEST_RADII)} different radius values...")
    
    # Check system info
    print(f"\nSystem Info:")
    print(f"CPU cores: {psutil.cpu_count()}")
    print(f"Available memory: {psutil.virtual_memory().available / 1024 / 1024 / 1024:.1f}GB")
    
    results = []
    total_start = time.time()
    
    for radius in TEST_RADII:
        result = test_radius_performance(radius)
        results.append(result)
        
        # Small delay between tests
        time.sleep(1)
    
    total_end = time.time()
    
    print(f"\nAll tests completed in {total_end - total_start:.2f}s")
    
    # Analyze results
    analyze_results(results)
    
    # Save results summary
    successful_count = sum(1 for r in results if r['success'])
    print(f"\nSummary: {successful_count}/{len(results)} tests successful")

if __name__ == "__main__":
    main() 