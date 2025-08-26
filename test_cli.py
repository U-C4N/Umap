"""
CLI Test Script for Umap v3.0
Bu dosya CLI fonksiyonlarını test eder.
"""
import subprocess
import sys
import os
import tempfile
from pathlib import Path

def run_command(cmd):
    """Komut çalıştır ve sonucu döndür"""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=60
        )
        return result
    except subprocess.TimeoutExpired:
        return None

def test_cli_help():
    """CLI help komutlarını test et"""
    print("\n📋 Testing CLI help commands...")
    
    commands = [
        "python -m umap --help",
        "python -m umap create --help",
        "python -m umap batch --help"
    ]
    
    for cmd in commands:
        print(f"   Testing: {cmd}")
        result = run_command(cmd)
        
        if result and result.returncode == 0:
            print(f"   ✅ {cmd} - OK")
        else:
            print(f"   ❌ {cmd} - FAILED")
            if result:
                print(f"      Error: {result.stderr}")

def test_cli_create_command():
    """CLI create komutunu test et"""
    print("\n🗺️ Testing CLI create command...")
    
    # Geçici output dosyası
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
        output_path = tmp_file.name
    
    try:
        # Test komutu - küçük bir harita oluştur
        cmd = f'python -m umap create --coords "41.0082,28.9784" --radius 1000 --style minimal --output "{output_path}" -v'
        
        print(f"   Running: {cmd}")
        result = run_command(cmd)
        
        if result:
            if result.returncode == 0:
                print("   ✅ CLI create command successful")
                
                # Dosya oluştu mu kontrol et
                if os.path.exists(output_path):
                    size = os.path.getsize(output_path)
                    print(f"   ✅ Output file created: {size} bytes")
                else:
                    print("   ❌ Output file not created")
            else:
                print("   ❌ CLI create command failed")
                print(f"   Error: {result.stderr}")
                print(f"   Output: {result.stdout}")
        else:
            print("   ❌ Command timed out")
            
    finally:
        # Temizlik
        if os.path.exists(output_path):
            os.unlink(output_path)

def test_cli_styles():
    """CLI stil parametrelerini test et"""
    print("\n🎨 Testing CLI styles...")
    
    styles = ['minimal', 'blueprint', 'vintage']
    
    for style in styles:
        print(f"   Testing style: {style}")
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            output_path = tmp_file.name
        
        try:
            cmd = f'python -m umap create --coords "41.0082,28.9784" --radius 500 --style {style} --output "{output_path}"'
            result = run_command(cmd)
            
            if result and result.returncode == 0:
                if os.path.exists(output_path):
                    print(f"   ✅ Style '{style}' works")
                else:
                    print(f"   ❌ Style '{style}' - no output file")
            else:
                print(f"   ❌ Style '{style}' failed")
                
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

def test_cli_batch_processing():
    """CLI batch processing'i test et"""
    print("\n📦 Testing CLI batch processing...")
    
    # Test için locations dosyası oluştur
    locations_content = """# Test locations
Istanbul,41.0082,28.9784,1000
Ankara,39.9334,32.8597,1000
Izmir,38.4237,27.1428,1000"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
        tmp_file.write(locations_content)
        locations_file = tmp_file.name
    
    try:
        cmd = f'python -m umap batch --file "{locations_file}" --style minimal --format png'
        print(f"   Running: {cmd}")
        
        result = run_command(cmd)
        
        if result:
            if result.returncode == 0:
                print("   ✅ Batch processing successful")
                
                # Oluşturulan dosyaları kontrol et
                expected_files = ['Istanbul.png', 'Ankara.png', 'Izmir.png']
                created_files = []
                
                for filename in expected_files:
                    if os.path.exists(filename):
                        created_files.append(filename)
                        # Temizlik için sil
                        os.unlink(filename)
                
                print(f"   ✅ Created {len(created_files)} map files")
            else:
                print("   ❌ Batch processing failed")
                print(f"   Error: {result.stderr}")
        else:
            print("   ❌ Batch command timed out")
            
    finally:
        # Locations dosyasını temizle
        if os.path.exists(locations_file):
            os.unlink(locations_file)

def test_cli_verbosity():
    """CLI verbosity seviyelerini test et"""
    print("\n🔊 Testing CLI verbosity levels...")
    
    verbosity_levels = ['-v', '-vv']
    
    for level in verbosity_levels:
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            output_path = tmp_file.name
        
        try:
            cmd = f'python -m umap create --coords "41.0082,28.9784" --radius 500 --style minimal --output "{output_path}" {level}'
            result = run_command(cmd)
            
            if result and result.returncode == 0:
                # Stdout'da detaylı log var mı kontrol et
                if result.stdout and len(result.stdout) > 10:
                    print(f"   ✅ Verbosity {level} - detailed output")
                else:
                    print(f"   ⚠️  Verbosity {level} - minimal output")
            else:
                print(f"   ❌ Verbosity {level} failed")
                
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

def main():
    """Ana CLI test fonksiyonu"""
    print("🚀 Umap v3.0 CLI Test Paketi")
    print("=" * 40)
    
    # CLI testlerini çalıştır
    test_cli_help()
    test_cli_create_command()
    test_cli_styles()
    test_cli_verbosity()
    test_cli_batch_processing()
    
    print("\n📋 CLI Test Summary:")
    print("   • Help commands")
    print("   • Create command")
    print("   • Style parameters")
    print("   • Verbosity levels")
    print("   • Batch processing")

if __name__ == "__main__":
    main()
