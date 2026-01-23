#!/usr/bin/env python3
"""
Rip Current Flow Analysis
Calculates flow vectors from bathymetry gradients to visualize rip currents
"""

import numpy as np
import rasterio
from scipy.ndimage import gaussian_filter
import json
from pathlib import Path

def calculate_flow_vectors(bathymetry_tif, output_json, grid_spacing=20):
    """
    Calculate flow vectors from bathymetry gradients.
    Water flows from shallow to deep (following steepest descent).
    
    Args:
        bathymetry_tif: Path to clipped bathymetry GeoTIFF
        output_json: Path for output JSON with flow vectors
        grid_spacing: Spacing between flow vectors (in pixels)
    """
    print(f"Analyzing bathymetry: {bathymetry_tif}")
    
    with rasterio.open(bathymetry_tif) as src:
        data = src.read(1)
        transform = src.transform
        bounds = src.bounds
        height, width = data.shape
        
    # Smooth the data to reduce noise
    smoothed = gaussian_filter(data, sigma=2)
    
    # Calculate gradients (depth change)
    grad_y, grad_x = np.gradient(smoothed)
    
    # Flow magnitude (steepness)
    magnitude = np.sqrt(grad_x**2 + grad_y**2)
    
    # Normalize gradients to get flow direction
    with np.errstate(divide='ignore', invalid='ignore'):
        flow_x = grad_x / (magnitude + 1e-10)
        flow_y = grad_y / (magnitude + 1e-10)
    
    flow_x = np.nan_to_num(flow_x)
    flow_y = np.nan_to_num(flow_y)
    magnitude = np.nan_to_num(magnitude)
    
    # Sample flow vectors on a grid
    flow_vectors = []
    
    for i in range(0, height, grid_spacing):
        for j in range(0, width, grid_spacing):
            if magnitude[i, j] < np.nanpercentile(magnitude, 30):
                continue
            
            x, y = transform * (j, i)
            
            from pyproj import Transformer
            transformer = Transformer.from_crs(
                src.crs,
                "EPSG:4326",
                always_xy=True
            )
            lon, lat = transformer.transform(x, y)
            
            dx = float(flow_x[i, j])
            dy = float(flow_y[i, j])
            mag = float(magnitude[i, j])
            
            flow_vectors.append({
                'lat': lat,
                'lon': lon,
                'dx': dx,
                'dy': dy,
                'magnitude': mag
            })
    
    print(f"Generated {len(flow_vectors)} flow vectors")
    
    # Normalize magnitudes
    if flow_vectors:
        max_mag = max(v['magnitude'] for v in flow_vectors)
        for v in flow_vectors:
            v['magnitude'] /= max_mag
    
    output = {
        'bounds': {
            'south': bounds.bottom,
            'west': bounds.left,
            'north': bounds.top,
            'east': bounds.right
        },
        'flow_vectors': flow_vectors,
        'metadata': {
            'grid_spacing': grid_spacing,
            'total_vectors': len(flow_vectors)
        }
    }
    
    with open(output_json, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"Flow vectors saved to: {output_json}")
    return output


def export_depth_grid(bathymetry_tif, output_json, downsample=10):
    """
    Export a downsampled depth grid for web browser flow calculations.
    
    Args:
        bathymetry_tif: Path to bathymetry GeoTIFF
        output_json: Path for output JSON
        downsample: Downsample factor (10 = 1/10th resolution)
    """
    print(f"Exporting depth grid for browser...")
    
    with rasterio.open(bathymetry_tif) as src:
        data = src.read(1)
        transform = src.transform
        bounds = src.bounds
        
        from pyproj import Transformer
        transformer = Transformer.from_crs(
            src.crs,
            "EPSG:4326",
            always_xy=True
        )
        
    # Downsample for browser efficiency
    downsampled = data[::downsample, ::downsample]
    
    # Calculate flow direction at each grid point
    grad_y, grad_x = np.gradient(downsampled)
    magnitude = np.sqrt(grad_x**2 + grad_y**2)
    
    # Normalize
    with np.errstate(divide='ignore', invalid='ignore'):
        flow_x = grad_x / (magnitude + 1e-10)
        flow_y = grad_y / (magnitude + 1e-10)
    
    flow_x = np.nan_to_num(flow_x)
    flow_y = np.nan_to_num(flow_y)
    
    # Build grid structure
    height, width = downsampled.shape
    grid = []
    
    for i in range(height):
        row = []
        for j in range(width):
            # Get lat/lon for this grid cell
            px = j * downsample
            py = i * downsample
            x, y = transform * (px, py)
            lon, lat = transformer.transform(x, y)
            
            row.append({
                'lat': lat,
                'lon': lon,
                'depth': float(downsampled[i, j]) if not np.isnan(downsampled[i, j]) else None,
                'flow_x': float(flow_x[i, j]),
                'flow_y': float(flow_y[i, j])
            })
        grid.append(row)
    
    output = {
        'bounds': {
            'south': bounds.bottom,
            'west': bounds.left,
            'north': bounds.top,
            'east': bounds.right
        },
        'grid_size': {
            'rows': height,
            'cols': width
        },
        'grid': grid
    }
    
    with open(output_json, 'w') as f:
        json.dump(output, f)
    
    print(f"Depth grid exported: {output_json}")
    print(f"Grid size: {height}x{width} cells")
    return output


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate rip current flow visualization data from bathymetry'
    )
    parser.add_argument('--bathymetry', required=True,
                       help='Path to clipped bathymetry GeoTIFF')
    parser.add_argument('--output-dir', default='docs/maps',
                       help='Output directory for JSON files')
    parser.add_argument('--grid-spacing', type=int, default=15,
                       help='Spacing between flow vectors (pixels)')
    parser.add_argument('--downsample', type=int, default=10,
                       help='Downsample factor for browser grid')
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate flow vectors
    flow_json = output_dir / 'flow_vectors.json'
    calculate_flow_vectors(
        args.bathymetry,
        flow_json,
        grid_spacing=args.grid_spacing
    )
    
    # Export depth grid for browser
    grid_json = output_dir / 'depth_grid.json'
    export_depth_grid(
        args.bathymetry,
        grid_json,
        downsample=args.downsample
    )
    
    print("\n✓ Done! Flow data generated.")
    print(f"\nGenerated files:")
    print(f"  • {flow_json}")
    print(f"  • {grid_json}")
    print("\nNext steps:")
    print("  1. Copy these to your docs/maps/ directory")
    print("  2. Update website to load and use the flow data")
    print("  3. git add, commit, push!")


if __name__ == '__main__':
    main()
