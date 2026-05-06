#!/usr/bin/env python3
"""
Download all Sentinel-2 scenes for Port Stanley AOI
May - September 2025 (clear days only)

Uses Copernicus Data Space Ecosystem (new API)
Fixes: refreshes token before each download to avoid 401 expiry errors
Fixes: skips already-downloaded scenes
"""

import sys
import json
import requests
import zipfile
from pathlib import Path
from datetime import datetime

# Configuration
AOI_FILE = "port_bathymetry_CLI/aoi.geojson"
OUTPUT_DIR = "Sentinel-2 Data"
START_DATE = "2026-04-01"
END_DATE = "2026-04-28"
MAX_CLOUD_COVER = 20

# Copernicus credentials
USERNAME = "copernicus.stylus717@passinbox.com"
PASSWORD = "NKv8vhGT1ACu!Ae#dxsm"

def get_access_token():
    """Get a fresh access token from Copernicus."""
    url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    data = {
        "client_id": "cdse-public",
        "grant_type": "password",
        "username": USERNAME,
        "password": PASSWORD
    }
    response = requests.post(url, data=data)
    response.raise_for_status()
    return response.json()["access_token"]

def load_aoi():
    """Load AOI from geojson."""
    with open(AOI_FILE) as f:
        geojson = json.load(f)
    coords = geojson['features'][0]['geometry']['coordinates'][0]
    wkt_coords = ', '.join([f"{lon} {lat}" for lon, lat in coords])
    return f"POLYGON(({wkt_coords}))"

def search_products(footprint, token):
    """Search for Sentinel-2 products."""
    url = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
    params = {
        "$filter": f"Collection/Name eq 'SENTINEL-2' and "
                   f"OData.CSC.Intersects(area=geography'SRID=4326;{footprint}') and "
                   f"ContentDate/Start ge {START_DATE}T00:00:00.000Z and "
                   f"ContentDate/Start le {END_DATE}T23:59:59.999Z and "
                   f"Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' and att/OData.CSC.DoubleAttribute/Value le {MAX_CLOUD_COVER}) and "
                   f"contains(Name,'MSIL2A')",
        "$orderby": "ContentDate/Start asc",
        "$top": 1000
    }
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    return response.json()['value']

def is_already_downloaded(product_name, output_dir):
    """Check if a scene was already successfully downloaded and extracted."""
    extracted_path = Path(output_dir) / product_name
    zip_path = Path(output_dir) / (product_name.replace(".SAFE", "") + ".zip")
    return extracted_path.exists() or zip_path.exists()

def download_product(product_id, product_name, output_dir):
    """Download a single product with a fresh token."""
    # Get a fresh token right before downloading
    print(f"    Refreshing token...")
    token = get_access_token()

    url = f"https://zipper.dataspace.copernicus.eu/odata/v1/Products({product_id})/$value"
    headers = {"Authorization": f"Bearer {token}"}
    output_file = Path(output_dir) / f"{product_name}.zip"

    print(f"    Downloading: {product_name}")
    response = requests.get(url, headers=headers, stream=True)
    response.raise_for_status()

    total_size = int(response.headers.get('content-length', 0))
    downloaded = 0

    with open(output_file, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            downloaded += len(chunk)
            if total_size > 0:
                percent = (downloaded / total_size) * 100
                print(f"    Progress: {percent:.1f}%", end='\r')

    print(f"\n    ✓ Saved: {output_file}")

    print(f"    Extracting...")
    with zipfile.ZipFile(output_file, 'r') as zip_ref:
        zip_ref.extractall(output_dir)

    output_file.unlink()
    print(f"    ✓ Extracted")

def main():
    print("=" * 70)
    print("Downloading Sentinel-2 Data for Port Stanley")
    print("May - September 2025")
    print("=" * 70)

    # Initial auth just for searching
    print("\n1. Authenticating with Copernicus...")
    try:
        token = get_access_token()
        print("   ✓ Authenticated")
    except Exception as e:
        print(f"   ❌ Authentication failed: {e}")
        return

    print("\n2. Loading AOI...")
    footprint = load_aoi()
    print(f"   ✓ Port Stanley Beach AOI loaded")

    print(f"\n3. Searching for products...")
    print(f"   Date range: {START_DATE} to {END_DATE}")
    print(f"   Max cloud: {MAX_CLOUD_COVER}%")
    try:
        products = search_products(footprint, token)
        print(f"   ✓ Found {len(products)} scenes")
    except Exception as e:
        print(f"   ❌ Search failed: {e}")
        return

    if not products:
        print("\n❌ No products found matching criteria")
        return

    # Check which are already downloaded
    Path(OUTPUT_DIR).mkdir(exist_ok=True)
    already_done = [p for p in products if is_already_downloaded(p['Name'], OUTPUT_DIR)]
    to_download = [p for p in products if not is_already_downloaded(p['Name'], OUTPUT_DIR)]

    print(f"\n4. Status:")
    print(f"   ✓ Already downloaded: {len(already_done)}")
    print(f"   ↓ Still needed:       {len(to_download)}")

    if not to_download:
        print("\n✅ All scenes already downloaded!")
        print("\nNext step: python3 batch_process_2025.py")
        return

    print(f"\n   Scenes to download:")
    for i, p in enumerate(to_download, 1):
        date = p['ContentDate']['Start'][:10]
        print(f"   {i}. {date} - {p['Name'][:60]}...")

    response = input(f"\nDownload {len(to_download)} remaining scenes? (y/N): ")
    if response.lower() != 'y':
        print("Cancelled")
        return

    print(f"\n5. Downloading to: {OUTPUT_DIR}/")
    failed = []

    for i, product in enumerate(to_download, 1):
        print(f"\n  [{i}/{len(to_download)}] {product['Name']}")
        try:
            download_product(product['Id'], product['Name'], OUTPUT_DIR)
        except Exception as e:
            print(f"    ❌ Download failed: {e}")
            failed.append(product['Name'])
            continue

    print("\n" + "=" * 70)
    total_done = len(already_done) + (len(to_download) - len(failed))
    print(f"✅ Done! {total_done}/24 scenes ready")
    if failed:
        print(f"❌ {len(failed)} failed: {', '.join([f[:30] for f in failed])}")
    print("=" * 70)
    print("\nNext step: python3 batch_process_2025.py")

if __name__ == "__main__":
    main()
