#!/usr/bin/env python3
"""
Batch process all downloaded Sentinel-2 scenes for Port Stanley
May - September 2025

Run from project root:
    python3 batch_process_2025.py
"""

import subprocess
import sys
from pathlib import Path

# Configuration
SENTINEL_DIR = "Sentinel-2 Data"
AOI_FILE = "port_bathymetry_CLI/aoi.geojson"
OUTPUT_DIR = "output"
SCRIPT = "port_bathymetry_CLI/sentinel_bathymetry.py"

def main():
    sentinel_dir = Path(SENTINEL_DIR)
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(exist_ok=True)

    # Find all .SAFE directories
    scenes = sorted(sentinel_dir.glob("*.SAFE"))

    if not scenes:
        print(f"❌ No .SAFE directories found in '{SENTINEL_DIR}/'")
        sys.exit(1)

    print("=" * 70)
    print(f"Batch Processing {len(scenes)} Sentinel-2 Scenes")
    print("=" * 70)

    succeeded = []
    failed = []
    skipped = []

    for i, scene in enumerate(scenes, 1):
        # Extract date from filename e.g. S2C_MSIL2A_20250510T160841_...
        try:
            date_part = scene.name.split('_')[2][:8]  # 20250510
            date_str = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
            output_name = f"bathymetry_{date_part[:4]}_{date_part[4:6]}_{date_part[6:8]}"
        except (IndexError, ValueError):
            print(f"\n[{i}/{len(scenes)}] ⚠️  Could not parse date from: {scene.name}, skipping")
            skipped.append(scene.name)
            continue

        # Check if already processed (web PNG exists)
        web_png = output_dir / f"{output_name}_web.png"
        if web_png.exists():
            print(f"\n[{i}/{len(scenes)}] ✓ Already processed: {date_str} (skipping)")
            skipped.append(scene.name)
            succeeded.append((date_str, web_png))
            continue

        print(f"\n[{i}/{len(scenes)}] Processing: {date_str}")
        print(f"    Scene: {scene.name}")

        cmd = [
            sys.executable, SCRIPT,
            "process",
            "--scene", str(scene),
            "--aoi", AOI_FILE,
            "--output", output_name,
            "--output-dir", OUTPUT_DIR
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print(f"    ✓ Success: {web_png}")
                succeeded.append((date_str, web_png))
            else:
                print(f"    ❌ Failed!")
                print(f"    STDERR: {result.stderr[-500:] if result.stderr else 'none'}")
                failed.append((date_str, scene.name))

        except Exception as e:
            print(f"    ❌ Exception: {e}")
            failed.append((date_str, scene.name))

    # Summary
    print("\n" + "=" * 70)
    print("PROCESSING COMPLETE")
    print("=" * 70)
    print(f"✓ Processed: {len(succeeded)}")
    print(f"✗ Failed:    {len(failed)}")

    if failed:
        print(f"\nFailed scenes:")
        for date_str, name in failed:
            print(f"  - {date_str}: {name}")

    print(f"\nOutput PNGs ready in: {OUTPUT_DIR}/")
    print("\nNext step: publish to website with:")
    print("  python3 publish_to_website.py")

if __name__ == "__main__":
    main()
