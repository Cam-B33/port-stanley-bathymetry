#!/usr/bin/env python3
"""
Load Bathymetry Data into PostGIS
Imports processed GeoTIFF files into the database for analysis
"""

import sys
import argparse
from pathlib import Path
import numpy as np
import rasterio
from rasterio.features import shapes
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
import json

# Database connection
DB_CONFIG = {
    'dbname': 'port_stanley_bathymetry',
    'user': 'bathymetry_user',
    'password': 'changeme123',
    'host': 'localhost'
}

class BathymetryLoader:
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.cursor = self.conn.cursor()
    
    def extract_metadata_from_filename(self, filename):
        """Extract date from filename like bathymetry_2025_09_30_clipped.tif"""
        stem = Path(filename).stem
        # Try to extract date pattern YYYY_MM_DD
        parts = stem.split('_')
        for i in range(len(parts) - 2):
            try:
                year = int(parts[i])
                month = int(parts[i+1])
                day = int(parts[i+2])
                if 2020 <= year <= 2030 and 1 <= month <= 12 and 1 <= day <= 31:
                    return datetime(year, month, day).date()
            except (ValueError, IndexError):
                continue
        return None
    
    def insert_scene(self, scene_name, acquisition_date):
        """Insert or get scene record."""
        # Check if exists
        self.cursor.execute(
            "SELECT id FROM scenes WHERE scene_name = %s",
            (scene_name,)
        )
        result = self.cursor.fetchone()
        if result:
            return result[0]
        
        # Insert new
        self.cursor.execute("""
            INSERT INTO scenes (scene_name, acquisition_date, processing_date, quality)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (scene_name, acquisition_date, datetime.now(), 'good'))
        
        scene_id = self.cursor.fetchone()[0]
        self.conn.commit()
        return scene_id
    
    def load_bathymetry_raster(self, geotiff_path, scene_id):
        """Load raster metadata and statistics."""
        print(f"  Loading raster metadata...")
        
        with rasterio.open(geotiff_path) as src:
            data = src.read(1)
            bounds = src.bounds
            
            # Calculate statistics
            valid_data = data[~np.isnan(data)]
            if len(valid_data) == 0:
                print("  ⚠️  No valid data in raster")
                return None
            
            stats = {
                'min_depth': float(np.min(valid_data)),
                'max_depth': float(np.max(valid_data)),
                'mean_depth': float(np.mean(valid_data)),
                'std_depth': float(np.std(valid_data)),
                'valid_pixels': int(len(valid_data))
            }
            
            # Create bounds polygon (WKT)
            bounds_wkt = f"POLYGON(({bounds.left} {bounds.bottom}, {bounds.right} {bounds.bottom}, {bounds.right} {bounds.top}, {bounds.left} {bounds.top}, {bounds.left} {bounds.bottom}))"
            
            # Insert
            self.cursor.execute("""
                INSERT INTO bathymetry_rasters 
                (scene_id, file_path, min_depth, max_depth, mean_depth, std_depth, valid_pixels, bounds)
                VALUES (%s, %s, %s, %s, %s, %s, %s, ST_GeomFromText(%s, 4326))
                RETURNING id
            """, (
                scene_id,
                str(geotiff_path),
                stats['min_depth'],
                stats['max_depth'],
                stats['mean_depth'],
                stats['std_depth'],
                stats['valid_pixels'],
                bounds_wkt
            ))
            
            raster_id = self.cursor.fetchone()[0]
            self.conn.commit()
            
            print(f"    ✓ Depth range: {stats['min_depth']:.2f} to {stats['max_depth']:.2f}m")
            print(f"    ✓ Mean: {stats['mean_depth']:.2f}m ± {stats['std_depth']:.2f}m")
            print(f"    ✓ Valid pixels: {stats['valid_pixels']:,}")
            
            return raster_id
    
    def load_bathymetry_points(self, geotiff_path, scene_id, grid_spacing=10):
        """
        Load bathymetry as point grid.
        
        Args:
            grid_spacing: Sample every Nth pixel (default 10 = 100m spacing)
        """
        print(f"  Loading bathymetry points (sampling every {grid_spacing} pixels)...")
        
        with rasterio.open(geotiff_path) as src:
            data = src.read(1)
            transform = src.transform
            
            # Sample at grid spacing
            points = []
            rows, cols = data.shape
            
            for i in range(0, rows, grid_spacing):
                for j in range(0, cols, grid_spacing):
                    depth = data[i, j]
                    if not np.isnan(depth):
                        # Convert pixel coords to lat/lon
                        lon, lat = rasterio.transform.xy(transform, i, j)
                        
                        # Calculate gradients (if not on edge)
                        gradient_x = gradient_y = gradient_mag = None
                        if 1 < i < rows-1 and 1 < j < cols-1:
                            dx = (data[i, j+1] - data[i, j-1]) / 2
                            dy = (data[i+1, j] - data[i-1, j]) / 2
                            gradient_x = float(dx) if not np.isnan(dx) else None
                            gradient_y = float(dy) if not np.isnan(dy) else None
                            if gradient_x is not None and gradient_y is not None:
                                gradient_mag = float(np.sqrt(dx**2 + dy**2))
                        
                        points.append((
                            scene_id,
                            lon, lat,
                            float(depth),
                            gradient_x,
                            gradient_y,
                            gradient_mag,
                            j, i  # grid coords
                        ))
            
            if not points:
                print("  ⚠️  No valid points found")
                return 0
            
            # Batch insert
            execute_values(
                self.cursor,
                """
                INSERT INTO bathymetry_points 
                (scene_id, location, depth, gradient_x, gradient_y, gradient_magnitude, grid_x, grid_y)
                VALUES %s
                """,
                [(p[0], f'POINT({p[1]} {p[2]})', p[3], p[4], p[5], p[6], p[7], p[8]) for p in points],
                template="(%s, ST_GeomFromText(%s, 4326), %s, %s, %s, %s, %s, %s)"
            )
            
            self.conn.commit()
            print(f"    ✓ Loaded {len(points):,} points")
            
            return len(points)
    
    def load_rip_zones(self, json_path, scene_id):
        """Load rip current risk zones from JSON."""
        print(f"  Loading rip risk zones...")
        
        if not Path(json_path).exists():
            print(f"    ⚠️  Risk zones file not found: {json_path}")
            return 0
        
        with open(json_path) as f:
            data = json.load(f)
        
        zones = []
        for flow_mode in ['east', 'west', 'offshore']:
            for zone in data['risk_zones'].get(flow_mode, []):
                zones.append((
                    scene_id,
                    flow_mode,
                    zone['risk'],
                    zone['lon'],
                    zone['lat']
                ))
        
        if not zones:
            print("    ⚠️  No risk zones found")
            return 0
        
        # Insert
        execute_values(
            self.cursor,
            """
            INSERT INTO rip_risk_zones 
            (scene_id, flow_mode, risk_level, zone_geom)
            VALUES %s
            """,
            zones,
            template="(%s, %s, %s, ST_GeomFromText('POINT(%s %s)', 4326))"
        )
        
        self.conn.commit()
        print(f"    ✓ Loaded {len(zones)} risk zones")
        
        return len(zones)
    
    def load_scene(self, output_name):
        """
        Load all data for a processed scene.
        
        Args:
            output_name: e.g., 'bathymetry_2025_09_30' or 'port_stanley_sept_30_2024'
        """
        base_path = Path("port_bathymetry_CLI/output")
        
        # Find GeoTIFF
        geotiff = base_path / f"{output_name}_clipped.tif"
        if not geotiff.exists():
            print(f"❌ GeoTIFF not found: {geotiff}")
            return False
        
        # Find risk zones
        risk_json = Path("docs/maps/rip_risk_zones.json")
        
        print(f"\n{'='*60}")
        print(f"Loading: {output_name}")
        print(f"{'='*60}")
        
        # Extract date
        acq_date = self.extract_metadata_from_filename(output_name)
        if not acq_date:
            print("❌ Could not extract date from filename")
            return False
        
        print(f"Acquisition date: {acq_date}")
        
        # Insert scene
        scene_id = self.insert_scene(output_name, acq_date)
        print(f"Scene ID: {scene_id}")
        
        # Load raster metadata
        self.load_bathymetry_raster(geotiff, scene_id)
        
        # Load point grid
        self.load_bathymetry_points(geotiff, scene_id, grid_spacing=10)
        
        # Load rip zones
        self.load_rip_zones(risk_json, scene_id)
        
        print(f"\n✅ Successfully loaded {output_name}")
        return True
    
    def close(self):
        self.cursor.close()
        self.conn.close()


def main():
    parser = argparse.ArgumentParser(description='Load bathymetry data into PostGIS')
    parser.add_argument('--scene', help='Scene output name (e.g., bathymetry_2025_09_30)')
    parser.add_argument('--all', action='store_true', help='Load all scenes from output directory')
    
    args = parser.parse_args()
    
    loader = BathymetryLoader()
    
    try:
        if args.all:
            # Find all processed scenes
            output_dir = Path("port_bathymetry_CLI/output")
            geotiffs = sorted(output_dir.glob("*_clipped.tif"))
            
            print(f"Found {len(geotiffs)} scenes to load")
            
            success = 0
            for geotiff in geotiffs:
                output_name = geotiff.stem.replace('_clipped', '')
                if loader.load_scene(output_name):
                    success += 1
            
            print(f"\n{'='*60}")
            print(f"✅ Loaded {success}/{len(geotiffs)} scenes successfully")
            print(f"{'='*60}")
            
        elif args.scene:
            loader.load_scene(args.scene)
        else:
            print("Usage: python3 load_bathymetry_data.py --scene [name] OR --all")
            return
    
    finally:
        loader.close()
    
    print("\nQuery your data:")
    print("  psql -U bathymetry_user -d port_stanley_bathymetry")
    print("  SELECT * FROM scenes;")


if __name__ == "__main__":
    main()
