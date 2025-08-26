"""
Test script for Umap v3.0 improvements.
Bu dosya yapılan mimari iyileştirmeleri test eder.
"""
import os
import sys
import time
import tempfile
from pathlib import Path

# Umap'i import et
try:
    import umap
    print(f"✅ Umap v{umap.__version__} successfully imported")
except ImportError as e:
    print(f"❌ Failed to import umap: {e}")
    sys.exit(1)

def test_version_consistency():
    """Test version tutarlılığı"""
    print("\n🔍 Testing version consistency...")
    
    version = umap.__version__
    print(f"   Package version: {version}")
    
    # pyproject.toml kontrolü
    try:
        with open('pyproject.toml', 'r') as f:
            content = f.read()
            if f'version = "{version}"' in content:
                print("   ✅ pyproject.toml version matches")
            else:
                print("   ❌ pyproject.toml version mismatch")
    except FileNotFoundError:
        print("   ⚠️  pyproject.toml not found")

def test_styles_system():
    """Test stil sistemi"""
    print("\n🎨 Testing styles system...")
    
    try:
        # Mevcut stilleri listele
        styles = umap.list_styles()
        print(f"   Available styles: {styles}")
        
        # Her stil için test
        for style_name in styles:
            style = umap.get_style(style_name)
            print(f"   ✅ Style '{style_name}' loaded successfully")
        
        # Özel stil ekleme testi
        custom_style = {
            'background': {'fc': '#test', 'zorder': -1},
            'streets': {'ec': '#test', 'lw': 1, 'zorder': 1}
        }
        umap.register_style('test_style', custom_style)
        
        if 'test_style' in umap.list_styles():
            print("   ✅ Custom style registration works")
        else:
            print("   ❌ Custom style registration failed")
            
    except Exception as e:
        print(f"   ❌ Styles system error: {e}")

def test_cache_system():
    """Test cache sistemi"""
    print("\n💾 Testing cache system...")
    
    try:
        # Cache bilgileri al
        cache_info = umap.get_cache_info()
        print(f"   Cache directory: {cache_info['cache_dir']}")
        print(f"   Cache files: {cache_info['file_count']}")
        print(f"   Cache size: {cache_info['total_size_mb']:.2f} MB")
        
        # Cache temizleme testi
        cleared = umap.clear_cache()
        print(f"   ✅ Cache cleared: {cleared} files removed")
        
    except Exception as e:
        print(f"   ❌ Cache system error: {e}")

def test_optimization_system():
    """Test optimization sistemi"""
    print("\n⚡ Testing optimization system...")
    
    try:
        # Farklı radius değerleri için optimizasyon testi
        radii = [500, 2000, 10000, 20000]
        
        for radius in radii:
            config = umap.auto_optimize_layers(radius)
            detail_level = config.get('detail', 'unknown')
            print(f"   Radius {radius}m -> Detail: {detail_level}")
        
        print("   ✅ Optimization system working")
        
    except Exception as e:
        print(f"   ❌ Optimization system error: {e}")

def test_basic_functionality():
    """Test temel fonksiyonellik"""
    print("\n🗺️  Testing basic functionality...")
    
    try:
        # Küçük bir test haritası oluştur
        print("   Creating test map...")
        
        # İstanbul koordinatları - küçük alan
        test_coords = (41.0082, 28.9784)
        test_radius = 1000  # 1km
        
        # Minimal stil ile hızlı test
        plot = umap.plot(
            test_coords,
            radius=test_radius,
            style='minimal',
            figsize=(6, 6),
            use_cache=True,
            auto_optimize=True
        )
        
        if plot.fig is not None:
            # Geçici dosyaya kaydet
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                plot.fig.savefig(tmp.name, dpi=100, bbox_inches='tight')
                print(f"   ✅ Test map created: {tmp.name}")
                
                # Dosya boyutunu kontrol et
                size = os.path.getsize(tmp.name)
                print(f"   File size: {size} bytes")
                
                # Temizlik
                os.unlink(tmp.name)
        else:
            print("   ❌ Failed to create test map")
            
    except Exception as e:
        print(f"   ❌ Basic functionality error: {e}")

def test_api_completeness():
    """Test API completeness"""
    print("\n📚 Testing API completeness...")
    
    expected_functions = [
        'plot', 'multiplot', 'Plot', 'Subplot', 'get_gdfs', 'add_frame',
        'get_style', 'list_styles', 'register_style',
        'get_cache', 'clear_cache', 'get_cache_info',
        'auto_optimize_layers', 'check_data_quality', 'get_processing_stats',
        'cli_main'
    ]
    
    missing = []
    for func_name in expected_functions:
        if hasattr(umap, func_name):
            print(f"   ✅ {func_name}")
        else:
            print(f"   ❌ {func_name} missing")
            missing.append(func_name)
    
    if not missing:
        print("   ✅ All API functions available")
    else:
        print(f"   ❌ Missing functions: {missing}")

def main():
    """Ana test fonksiyonu"""
    print("🚀 Umap v3.0 İyileştirmeler Test Paketi")
    print("=" * 50)
    
    start_time = time.time()
    
    # Testleri çalıştır
    test_version_consistency()
    test_api_completeness()
    test_styles_system()
    test_cache_system()
    test_optimization_system()
    test_basic_functionality()
    
    end_time = time.time()
    
    print(f"\n⏱️  Test completed in {end_time - start_time:.2f} seconds")
    print("\n📋 Test Summary:")
    print("   • Version consistency")
    print("   • API completeness")
    print("   • Styles system")
    print("   • Cache system")
    print("   • Optimization system")
    print("   • Basic functionality")

if __name__ == "__main__":
    main()
