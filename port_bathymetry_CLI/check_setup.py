#!/usr/bin/env python3
"""
Setup validation script
Checks if all dependencies are installed and configured correctly
"""

import sys
import importlib

def check_import(module_name, package_name=None):
    """Check if a Python module can be imported."""
    try:
        importlib.import_module(module_name)
        print(f"✓ {package_name or module_name}")
        return True
    except ImportError:
        print(f"✗ {package_name or module_name} - NOT FOUND")
        return False

def check_gdal():
    """Check GDAL with version info."""
    try:
        from osgeo import gdal
        version = gdal.__version__
        print(f"✓ GDAL (version {version})")
        return True
    except ImportError:
        print("✗ GDAL - NOT FOUND")
        print("  Install with: sudo apt-get install gdal-bin libgdal-dev python3-gdal")
        return False

def check_file(filename):
    """Check if a file exists."""
    from pathlib import Path
    if Path(filename).exists():
        print(f"✓ {filename} found")
        return True
    else:
        print(f"✗ {filename} - NOT FOUND")
        return False

def main():
    print("=" * 60)
    print("Sentinel-2 Bathymetry Processing - Setup Validation")
    print("=" * 60)
    print()
    
    print("Checking Python version...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
    else:
        print(f"✗ Python {version.major}.{version.minor}.{version.micro}")
        print("  Python 3.8 or higher required")
        return False
    
    print()
    print("Checking Python dependencies...")
    
    checks = [
        check_import("numpy"),
        check_import("rasterio"),
        check_gdal(),
        check_import("sentinelsat"),
        check_import("matplotlib"),
    ]
    
    print()
    print("Checking required files...")
    
    file_checks = [
        check_file("sentinel_bathymetry.py"),
        check_file("aoi_template.geojson"),
        check_file("requirements.txt"),
    ]
    
    print()
    print("Checking optional configuration...")
    
    config_exists = check_file("config.py")
    aoi_exists = check_file("aoi.geojson")
    
    print()
    print("=" * 60)
    
    if all(checks) and all(file_checks):
        print("✓ All required dependencies are installed!")
        print()
        
        if not config_exists:
            print("⚠ Next steps:")
            print("  1. Copy config_template.py to config.py")
            print("  2. Add your Copernicus Hub credentials to config.py")
        
        if not aoi_exists:
            print("  3. Create your AOI geojson file (or rename aoi_template.geojson)")
        
        print()
        print("Ready to process! Try:")
        print("  python sentinel_bathymetry.py --help")
        
        return True
    else:
        print("✗ Some dependencies are missing")
        print()
        print("Install missing dependencies with:")
        print("  pip install -r requirements.txt")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
