#!/usr/bin/env python3
"""
Sentinel-2 Nearshore Bathymetry Processing
Automated processing of Sentinel-2 imagery to generate relative bathymetry contours
for rip current identification at Port Stanley, Ontario beach.

Author: Your Name
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.mask import mask
from rasterio.plot import show
import matplotlib.pyplot as plt
from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SentinelBathymetryProcessor:
    """
    Process Sentinel-2 imagery to generate relative bathymetry maps
    using band ratio techniques for shallow water environments.
    """
    
    def __init__(self, output_dir="output", temp_dir="temp"):
        """
        Initialize the processor with output directories.
        
        Args:
            output_dir: Directory for final outputs
            temp_dir: Directory for temporary files
        """
        self.output_dir = Path(output_dir)
        self.temp_dir = Path(temp_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)
        
    def download_sentinel_data(self, aoi_geojson, start_date, end_date, 
                               username, password, max_cloud_cover=20):
        """
        Download Sentinel-2 imagery for the area of interest.
        
        Args:
            aoi_geojson: Path to GeoJSON file defining area of interest
            start_date: Start date for imagery search (YYYYMMDD)
            end_date: End date for imagery search (YYYYMMDD)
            username: Copernicus Open Access Hub username
            password: Copernicus Open Access Hub password
            max_cloud_cover: Maximum cloud cover percentage (0-100)
            
        Returns:
            List of downloaded product paths
        """
        logger.info(f"Connecting to Copernicus Hub...")
        api = SentinelAPI(username, password, 'https://scihub.copernicus.eu/dhus')
        
        # Read AOI
        footprint = geojson_to_wkt(read_geojson(aoi_geojson))
        
        # Search for products
        logger.info(f"Searching for imagery from {start_date} to {end_date}")
        products = api.query(
            footprint,
            date=(start_date, end_date),
            platformname='Sentinel-2',
            producttype='S2MSI2A',  # Level-2A (atmospherically corrected)
            cloudcoverpercentage=(0, max_cloud_cover)
        )
        
        logger.info(f"Found {len(products)} products")
        
        if len(products) == 0:
            logger.warning("No products found for the given criteria")
            return []
        
        # Download products
        downloaded = []
        for product_id, product_info in products.items():
            logger.info(f"Downloading: {product_info['title']}")
            api.download(product_id, directory_path=str(self.temp_dir))
            downloaded.append(product_id)
        
        return downloaded
    
    def calculate_bathymetry_ratio(self, blue_band_path, green_band_path, 
                                   red_band_path, output_path):
        """
        Calculate relative bathymetry using band ratio method.
        
        The log-ratio method: ln(Blue) / ln(Green) or ln(Green) / ln(Red)
        is commonly used for shallow water bathymetry.
        
        Args:
            blue_band_path: Path to blue band (B2) raster
            green_band_path: Path to green band (B3) raster
            red_band_path: Path to red band (B4) raster
            output_path: Path for output bathymetry raster
            
        Returns:
            Path to output raster
        """
        logger.info("Calculating bathymetry ratio...")
        
        # Read bands
        with rasterio.open(blue_band_path) as src_blue:
            blue = src_blue.read(1).astype(float)
            profile = src_blue.profile
            
        with rasterio.open(green_band_path) as src_green:
            green = src_green.read(1).astype(float)
            
        with rasterio.open(red_band_path) as src_red:
            red = src_red.read(1).astype(float)
        
        # Mask zero and negative values
        blue = np.where(blue <= 0, np.nan, blue)
        green = np.where(green <= 0, np.nan, green)
        red = np.where(red <= 0, np.nan, red)
        
        # Calculate log ratio - using Green/Red for nearshore shallow water
        # You can experiment with Blue/Green as well
        with np.errstate(divide='ignore', invalid='ignore'):
            bathymetry = np.log(green) / np.log(red)
        
        # Handle infinities and invalid values
        bathymetry = np.where(np.isinf(bathymetry), np.nan, bathymetry)
        
        # Update profile for output - force GeoTIFF driver
        profile.update(
            driver='GTiff',
            dtype=rasterio.float32,
            count=1,
            nodata=np.nan,
            compress='lzw'  # Add compression to reduce file size
        )
        
        # Write output
        with rasterio.open(output_path, 'w', **profile) as dst:
            dst.write(bathymetry.astype(rasterio.float32), 1)
        
        logger.info(f"Bathymetry raster saved to: {output_path}")
        return output_path
    
    def clip_to_aoi(self, input_raster, aoi_geojson, output_path):
        """
        Clip raster to area of interest.
        
        Args:
            input_raster: Path to input raster
            aoi_geojson: Path to GeoJSON defining AOI
            output_path: Path for clipped output
            
        Returns:
            Path to clipped raster
        """
        logger.info("Clipping to area of interest...")
        
        # Read AOI geometry
        with open(aoi_geojson) as f:
            geojson = json.load(f)
        
        # Extract geometry
        if geojson['type'] == 'FeatureCollection':
            geometries = [feature['geometry'] for feature in geojson['features']]
        else:
            geometries = [geojson['geometry']]
        
        # Open raster to get CRS
        with rasterio.open(input_raster) as src:
            raster_crs = src.crs
            
            # Reproject geometries to match raster CRS if needed
            from rasterio.warp import transform_geom
            reprojected_geoms = []
            
            # Assume GeoJSON is in WGS84 (EPSG:4326) if no CRS specified
            src_crs = 'EPSG:4326'
            
            for geom in geometries:
                if raster_crs != src_crs:
                    reprojected_geom = transform_geom(src_crs, raster_crs, geom)
                    reprojected_geoms.append(reprojected_geom)
                else:
                    reprojected_geoms.append(geom)
            
            # Clip raster
            try:
                out_image, out_transform = mask(src, reprojected_geoms, crop=True)
                out_meta = src.meta.copy()
            except ValueError as e:
                logger.error(f"AOI does not overlap with raster: {e}")
                logger.error(f"Raster CRS: {raster_crs}")
                logger.error(f"Raster bounds: {src.bounds}")
                logger.error("Please check your AOI coordinates cover the area in the imagery")
                raise
        
        # Update metadata
        out_meta.update({
            "driver": "GTiff",
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform
        })
        
        # Write clipped raster
        with rasterio.open(output_path, "w", **out_meta) as dest:
            dest.write(out_image)
        
        logger.info(f"Clipped raster saved to: {output_path}")
        return output_path
    
    def create_visualization(self, bathymetry_raster, output_image, 
                            title="Nearshore Bathymetry", cmap="viridis_r",
                            add_contours=True, contour_interval=None):
        """
        Create a visualization of the bathymetry map.
        
        Args:
            bathymetry_raster: Path to bathymetry raster
            output_image: Path for output image (PNG)
            title: Title for the map
            cmap: Matplotlib colormap name
            add_contours: Whether to add contour lines
            contour_interval: Spacing between contours (auto if None)
        """
        logger.info("Creating visualization...")
        
        with rasterio.open(bathymetry_raster) as src:
            data = src.read(1)
            transform = src.transform
            
        # Create figure
        fig, ax = plt.subplots(figsize=(14, 12))
        
        # Plot bathymetry as colored background
        im = ax.imshow(data, cmap=cmap, interpolation='bilinear', alpha=0.7)
        
        # Add contour lines if requested
        if add_contours:
            # Calculate contour levels
            valid_data = data[~np.isnan(data)]
            if len(valid_data) > 0:
                data_min, data_max = np.nanmin(data), np.nanmax(data)
                
                if contour_interval is None:
                    # Auto-calculate interval based on data range
                    # Reduced from 15 to 8 contours for cleaner look
                    data_range = data_max - data_min
                    contour_interval = data_range / 8
                
                levels = np.arange(
                    np.floor(data_min / contour_interval) * contour_interval,
                    np.ceil(data_max / contour_interval) * contour_interval,
                    contour_interval
                )
                
                # Create contours with reduced density
                contours = ax.contour(
                    data, 
                    levels=levels,
                    colors='purple',
                    linewidths=1.0,  # Slightly thicker lines
                    alpha=0.5  # More transparent
                )
                
                # Skip contour labels for cleaner look
                # Uncomment the next line if you want labels back
                # ax.clabel(contours, inline=True, fontsize=8, fmt='%.2f')
        
        ax.set_title(title, fontsize=16, pad=20, weight='bold')
        ax.axis('off')
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label('Relative Depth\n(lighter = shallower)', 
                      rotation=270, labelpad=25, fontsize=11)
        
        # Save
        plt.tight_layout()
        plt.savefig(output_image, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        logger.info(f"Visualization saved to: {output_image}")
        return output_image
    
    def create_web_overlay(self, bathymetry_raster, output_image, add_contours=True):
        """
        Create a clean bathymetry overlay for web mapping (no title, no colorbar).
        Just the bathymetry data with optional contours.
        
        Args:
            bathymetry_raster: Path to bathymetry GeoTIFF
            output_image: Path for output PNG
            add_contours: Whether to add contour lines
            
        Returns:
            Path to output image
        """
        logger.info(f"Creating web overlay: {output_image}")
        
        with rasterio.open(bathymetry_raster) as src:
            data = src.read(1)
        
        # Create figure with exact data dimensions (no padding)
        fig, ax = plt.subplots(figsize=(10, 7))
        
        # Custom colormap (yellow=shallow, teal=medium, purple=deep)
        colors = ['#f7f7b3', '#a8ddb5', '#43a2ca', '#0868ac', '#084081']
        n_bins = 100
        cmap = plt.cm.colors.LinearSegmentedColormap.from_list('bathymetry', colors, N=n_bins)
        
        # Display bathymetry data only
        im = ax.imshow(data, cmap=cmap, interpolation='bilinear', alpha=0.9)
        
        # Add contour lines if requested
        if add_contours:
            valid_data = data[~np.isnan(data)]
            if len(valid_data) > 0:
                data_min, data_max = np.nanmin(data), np.nanmax(data)
                data_range = data_max - data_min
                contour_interval = data_range / 8
                
                levels = np.arange(
                    np.floor(data_min / contour_interval) * contour_interval,
                    np.ceil(data_max / contour_interval) * contour_interval,
                    contour_interval
                )
                
                ax.contour(
                    data, 
                    levels=levels,
                    colors='purple',
                    linewidths=1.0,
                    alpha=0.5
                )
        
        # Remove all axes, labels, and padding
        ax.axis('off')
        ax.set_aspect('equal')
        
        # Save with no padding or borders
        plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
        plt.savefig(output_image, dpi=150, bbox_inches='tight', 
                   pad_inches=0, facecolor='none', transparent=True)
        plt.close()
        
        logger.info(f"Web overlay saved to: {output_image}")
        return output_image
    
    def generate_contours_shapefile(self, bathymetry_raster, output_shapefile,
                                    contour_interval=None):
        """
        Generate contour lines as a shapefile for use in GIS/web mapping.
        
        Args:
            bathymetry_raster: Path to bathymetry raster
            output_shapefile: Path for output shapefile
            contour_interval: Spacing between contours (auto if None)
            
        Returns:
            Path to output shapefile
        """
        logger.info("Generating contour shapefile...")
        
        try:
            import geopandas as gpd
            from rasterio import features
            from shapely.geometry import LineString, shape
        except ImportError:
            logger.warning("geopandas not installed, skipping contour shapefile generation")
            logger.info("Install with: pip install geopandas")
            return None
        
        with rasterio.open(bathymetry_raster) as src:
            data = src.read(1)
            transform = src.transform
            crs = src.crs
            
        # Calculate contour levels
        valid_data = data[~np.isnan(data)]
        if len(valid_data) == 0:
            logger.warning("No valid data for contours")
            return None
            
        data_min, data_max = np.nanmin(data), np.nanmax(data)
        
        if contour_interval is None:
            data_range = data_max - data_min
            contour_interval = data_range / 15
        
        levels = np.arange(
            np.floor(data_min / contour_interval) * contour_interval,
            np.ceil(data_max / contour_interval) * contour_interval,
            contour_interval
        )
        
        # Generate contours
        contours_list = []
        for level in levels:
            try:
                # Generate contour at this level
                contour_gen = features.shapes(
                    (data >= level).astype('uint8'),
                    transform=transform
                )
                
                for geom, value in contour_gen:
                    if value == 1:
                        contours_list.append({
                            'geometry': shape(geom),
                            'depth': level
                        })
            except Exception as e:
                logger.debug(f"Could not generate contour at level {level}: {e}")
                continue
        
        if len(contours_list) == 0:
            logger.warning("No contours generated")
            return None
        
        # Create GeoDataFrame
        gdf = gpd.GeoDataFrame(contours_list, crs=crs)
        
        # Save to shapefile
        gdf.to_file(output_shapefile)
        
        logger.info(f"Contour shapefile saved to: {output_shapefile}")
        return output_shapefile
    
    def process_scene(self, scene_dir, aoi_geojson, output_name=None):
        """
        Process a single Sentinel-2 scene to generate bathymetry map.
        
        Args:
            scene_dir: Path to Sentinel-2 SAFE directory
            aoi_geojson: Path to GeoJSON defining area of interest
            output_name: Custom name for output files
            
        Returns:
            Dictionary with paths to output files
        """
        scene_path = Path(scene_dir)
        
        if output_name is None:
            output_name = f"bathymetry_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Processing scene: {scene_path.name}")
        
        # Find band files (adjust paths based on Sentinel-2 structure)
        # For L2A products: .../GRANULE/.../IMG_DATA/R10m/
        granule_dir = list(scene_path.glob("GRANULE/*/IMG_DATA/R10m"))
        
        if not granule_dir:
            logger.error("Could not find IMG_DATA/R10m directory")
            return None
        
        img_dir = granule_dir[0]
        
        # Find band files
        blue_band = list(img_dir.glob("*B02_10m.jp2"))
        green_band = list(img_dir.glob("*B03_10m.jp2"))
        red_band = list(img_dir.glob("*B04_10m.jp2"))
        
        if not (blue_band and green_band and red_band):
            logger.error("Could not find required band files (B02, B03, B04)")
            return None
        
        # Calculate bathymetry
        bathymetry_path = self.output_dir / f"{output_name}_bathymetry.tif"
        self.calculate_bathymetry_ratio(
            str(blue_band[0]),
            str(green_band[0]),
            str(red_band[0]),
            str(bathymetry_path)
        )
        
        # Clip to AOI
        clipped_path = self.output_dir / f"{output_name}_clipped.tif"
        self.clip_to_aoi(
            str(bathymetry_path),
            aoi_geojson,
            str(clipped_path)
        )
        
        # Create visualization with contours
        viz_path = self.output_dir / f"{output_name}.png"
        self.create_visualization(
            str(clipped_path),
            str(viz_path),
            title=f"Port Stanley Nearshore Bathymetry - {output_name}",
            add_contours=True
        )
        
        # Create clean web overlay (no title, no colorbar)
        web_overlay_path = self.output_dir / f"{output_name}_web.png"
        self.create_web_overlay(
            str(clipped_path),
            str(web_overlay_path),
            add_contours=True
        )
        
        # Optionally generate contour shapefile for GIS use
        contour_shp = self.output_dir / f"{output_name}_contours.shp"
        self.generate_contours_shapefile(
            str(clipped_path),
            str(contour_shp)
        )
        
        result = {
            'bathymetry_raster': str(bathymetry_path),
            'clipped_raster': str(clipped_path),
            'visualization': str(viz_path),
            'web_overlay': str(web_overlay_path)
        }
        
        if contour_shp.exists():
            result['contours_shapefile'] = str(contour_shp)
        
        return result


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description='Process Sentinel-2 imagery for nearshore bathymetry mapping',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a local Sentinel-2 scene
  python sentinel_bathymetry.py process --scene /path/to/S2_SAFE --aoi aoi.geojson
  
  # Download and process imagery for date range
  python sentinel_bathymetry.py download-and-process --aoi aoi.geojson \\
      --start-date 20240601 --end-date 20240610 \\
      --username your_username --password your_password
  
  # Process with custom output name
  python sentinel_bathymetry.py process --scene /path/to/S2_SAFE --aoi aoi.geojson \\
      --output june_10_2024
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Process command
    process_parser = subparsers.add_parser('process', help='Process a local Sentinel-2 scene')
    process_parser.add_argument('--scene', required=True, help='Path to Sentinel-2 SAFE directory')
    process_parser.add_argument('--aoi', required=True, help='Path to AOI GeoJSON file')
    process_parser.add_argument('--output', help='Custom output name (optional)')
    process_parser.add_argument('--output-dir', default='output', help='Output directory')
    
    # Download and process command
    download_parser = subparsers.add_parser(
        'download-and-process', 
        help='Download Sentinel-2 imagery and process'
    )
    download_parser.add_argument('--aoi', required=True, help='Path to AOI GeoJSON file')
    download_parser.add_argument('--start-date', required=True, help='Start date (YYYYMMDD)')
    download_parser.add_argument('--end-date', required=True, help='End date (YYYYMMDD)')
    download_parser.add_argument('--username', required=True, help='Copernicus Hub username')
    download_parser.add_argument('--password', required=True, help='Copernicus Hub password')
    download_parser.add_argument('--max-cloud', type=int, default=20, 
                                help='Maximum cloud cover percentage (default: 20)')
    download_parser.add_argument('--output-dir', default='output', help='Output directory')
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    
    # Initialize processor
    processor = SentinelBathymetryProcessor(output_dir=args.output_dir)
    
    if args.command == 'process':
        # Process existing scene
        result = processor.process_scene(
            args.scene,
            args.aoi,
            output_name=args.output
        )
        
        if result:
            logger.info("Processing complete!")
            logger.info(f"Outputs:")
            for key, path in result.items():
                logger.info(f"  {key}: {path}")
        else:
            logger.error("Processing failed")
            sys.exit(1)
    
    elif args.command == 'download-and-process':
        # Download and process
        downloaded = processor.download_sentinel_data(
            args.aoi,
            args.start_date,
            args.end_date,
            args.username,
            args.password,
            max_cloud_cover=args.max_cloud
        )
        
        if not downloaded:
            logger.warning("No scenes downloaded, nothing to process")
            sys.exit(0)
        
        # Process each downloaded scene
        for scene_id in downloaded:
            # Find the downloaded SAFE directory
            safe_dirs = list(processor.temp_dir.glob(f"*{scene_id}*.SAFE"))
            if safe_dirs:
                scene_dir = safe_dirs[0]
                result = processor.process_scene(
                    str(scene_dir),
                    args.aoi,
                    output_name=scene_id[:15]  # Use product date as name
                )
                
                if result:
                    logger.info(f"Processed {scene_id}")
                else:
                    logger.error(f"Failed to process {scene_id}")


if __name__ == "__main__":
    main()
