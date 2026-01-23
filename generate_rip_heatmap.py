#!/usr/bin/env python3
"""
Rip Current Risk Analysis with Heat Map Generation
Calculates rip current risk zones based on bathymetry and flow direction
"""

import numpy as np
import rasterio
from scipy.ndimage import gaussian_filter
import json
from pathlib import Path
from scipy.ndimage import generic_filter

def calculate_rip_risk_zones(bathymetry_tif, output_json, grid_resolution=20):
    """
    Calculate rip current risk zones for different current directions.
    
    Creates heat maps showing where water converges and flows offshore,
    indicating high rip current danger.
    
    Args:
        bathymetry_tif: Path to bathymetry GeoTIFF
        output_json: Path for output JSON with risk zones
        grid_resolution: Grid spacing for risk calculation
    """
    print(f"Analyzing rip current risk zones...")
    
    with rasterio.open(bathymetry_tif) as src:
        data = src.read(1)
        transform = src.transform
        bounds = src.bounds
        height, width = data.shape
        
        from pyproj import Transformer
        transformer = Transformer.from_crs(
            src.crs,
            "EPSG:4326",
            always_xy=True
        )
    
    # Smooth data
    smoothed = gaussian_filter(data, sigma=2)
    
    # Calculate gradients (flow direction)
    grad_y, grad_x = np.gradient(smoothed)
    
    # Calculate flow magnitude (steepness = flow strength)
    magnitude = np.sqrt(grad_x**2 + grad_y**2)
    
    # Normalize gradients
    with np.errstate(divide='ignore', invalid='ignore'):
        flow_x = grad_x / (magnitude + 1e-10)
        flow_y = grad_y / (magnitude + 1e-10)
    
    flow_x = np.nan_to_num(flow_x)
    flow_y = np.nan_to_num(flow_y)
    magnitude = np.nan_to_num(magnitude)
    
    # Calculate divergence (flow convergence/divergence)
    # Negative divergence = convergence (water piling up) = RIP RISK
    div_x = np.gradient(flow_x, axis=1)
    div_y = np.gradient(flow_y, axis=0)
    divergence = div_x + div_y
    
    # Create risk zones for different current directions
    risk_zones = {
        'east': [],
        'west': [],
        'offshore': []
    }
    
    # Sample on a grid
    for i in range(0, height, grid_resolution):
        for j in range(0, width, grid_resolution):
            if np.isnan(data[i, j]):
                continue
            
            # Get geographic coordinates
            x, y = transform * (j, i)
            lon, lat = transformer.transform(x, y)
            
            # Calculate risk for each current direction
            
            # EAST CURRENT: Eastward flow + convergence + offshore component
            east_flow = flow_x[i, j]  # Positive = eastward
            offshore_component = -flow_y[i, j]  # Negative flow_y = offshore (south)
            convergence = -divergence[i, j]  # Negative div = convergence
            
            # East current risk: strong eastward flow + convergence + offshore
            # Increased multiplier for shallow nearshore bathymetry
            east_risk = (
                max(0, east_flow) * 0.4 +  # Eastward flow
                max(0, convergence) * 0.3 +  # Water piling up
                max(0, offshore_component) * 0.3  # Offshore flow
            ) * magnitude[i, j] * 100  # Increased from 10 to 100
            
            # WEST CURRENT: Same but westward
            west_flow = -flow_x[i, j]  # Negative = westward
            west_risk = (
                max(0, west_flow) * 0.4 +
                max(0, convergence) * 0.3 +
                max(0, offshore_component) * 0.3
            ) * magnitude[i, j] * 100  # Increased from 10 to 100
            
            # OFFSHORE: Pure bathymetry-driven offshore flow
            offshore_risk = (
                max(0, offshore_component) * 0.6 +
                max(0, convergence) * 0.4
            ) * magnitude[i, j] * 100  # Increased from 10 to 100
            
            # Only add cells with any risk (very low threshold)
            if east_risk > 0.001:
                risk_zones['east'].append({
                    'lat': lat,
                    'lon': lon,
                    'risk': min(1.0, float(east_risk))
                })
            
            if west_risk > 0.001:
                risk_zones['west'].append({
                    'lat': lat,
                    'lon': lon,
                    'risk': min(1.0, float(west_risk))
                })
            
            if offshore_risk > 0.001:
                risk_zones['offshore'].append({
                    'lat': lat,
                    'lon': lon,
                    'risk': min(1.0, float(offshore_risk))
                })
    
    # Normalize risks to 0-1 range for each direction
    for direction in ['east', 'west', 'offshore']:
        if risk_zones[direction]:
            max_risk = max(z['risk'] for z in risk_zones[direction])
            if max_risk > 0:
                for zone in risk_zones[direction]:
                    zone['risk'] = zone['risk'] / max_risk
    
    # Get geographic bounds in WGS84
    sw_x, sw_y = bounds.left, bounds.bottom
    ne_x, ne_y = bounds.right, bounds.top
    sw_lon, sw_lat = transformer.transform(sw_x, sw_y)
    ne_lon, ne_lat = transformer.transform(ne_x, ne_y)
    
    output = {
        'bounds': {
            'south': sw_lat,
            'west': sw_lon,
            'north': ne_lat,
            'east': ne_lon
        },
        'risk_zones': risk_zones,
        'metadata': {
            'description': 'Rip current risk heat map for different flow directions',
            'risk_scale': '0 = safe, 1 = extreme danger',
            'grid_resolution': grid_resolution
        }
    }
    
    with open(output_json, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"Risk zones calculated:")
    print(f"  East current: {len(risk_zones['east'])} risk cells")
    print(f"  West current: {len(risk_zones['west'])} risk cells")
    print(f"  Offshore: {len(risk_zones['offshore'])} risk cells")
    print(f"Saved to: {output_json}")
    
    return output


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate rip current risk heat maps from bathymetry'
    )
    parser.add_argument('--bathymetry', required=True,
                       help='Path to clipped bathymetry GeoTIFF')
    parser.add_argument('--output', default='docs/maps/rip_risk_zones.json',
                       help='Output JSON file')
    parser.add_argument('--grid-resolution', type=int, default=15,
                       help='Grid spacing for risk calculation')
    
    args = parser.parse_args()
    
    calculate_rip_risk_zones(
        args.bathymetry,
        args.output,
        grid_resolution=args.grid_resolution
    )
    
    print("\n✓ Risk zones generated!")
    print("Next: Update website to display the heat map")


if __name__ == '__main__':
    main()
