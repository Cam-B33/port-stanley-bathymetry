# Sentinel-2 Nearshore Bathymetry Processing

Automated processing of Sentinel-2 satellite imagery to generate relative bathymetry maps for identifying channelized rip currents at Port Stanley, Ontario beach.

## Overview

This tool uses Sentinel-2 multispectral imagery and band ratio techniques to create relative bathymetry contours of nearshore environments. The log-ratio method applied to visible bands (blue, green, red) can reveal underwater features including sandbars, channels, and rip current pathways.

## Installation

### Prerequisites

- Python 3.8 or higher
- GDAL/OGR libraries installed on your system

#### Installing GDAL

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install gdal-bin libgdal-dev python3-gdal
```

**macOS (with Homebrew):**
```bash
brew install gdal
```

**Windows:**
Download OSGeo4W installer from https://trac.osgeo.org/osgeo4w/

### Python Dependencies

```bash
pip install -r requirements.txt
```

## Configuration

1. **Set up Copernicus Hub account:**
   - Register at https://scihub.copernicus.eu/dhus/#/self-registration
   - Note your username and password

2. **Create your Area of Interest (AOI):**
   - Use QGIS or geojson.io to create a polygon around Port Stanley beach
   - Save as GeoJSON file (e.g., `aoi.geojson`)
   - A template is provided in `aoi_template.geojson`

3. **Configure settings (optional):**
   ```bash
   cp config_template.py config.py
   # Edit config.py with your credentials and preferences
   ```

## Usage

### Basic Usage - Process Local Scene

If you already have Sentinel-2 data downloaded:

```bash
python sentinel_bathymetry.py process \
    --scene /path/to/S2A_MSIL2A_*.SAFE \
    --aoi aoi.geojson \
    --output port_stanley_2024_06_10
```

### Download and Process

Automatically download recent imagery and process:

```bash
python sentinel_bathymetry.py download-and-process \
    --aoi aoi.geojson \
    --start-date 20240601 \
    --end-date 20240610 \
    --username your_username \
    --password your_password \
    --max-cloud 20
```

### Automated Processing (Every 10 Days)

Create a bash script `process_latest.sh`:

```bash
#!/bin/bash

# Calculate date range (last 10 days)
END_DATE=$(date +%Y%m%d)
START_DATE=$(date -d "10 days ago" +%Y%m%d)

# Run processing
python sentinel_bathymetry.py download-and-process \
    --aoi aoi.geojson \
    --start-date $START_DATE \
    --end-date $END_DATE \
    --username $COPERNICUS_USER \
    --password $COPERNICUS_PASS \
    --max-cloud 20
```

Make it executable:
```bash
chmod +x process_latest.sh
```

Set up a cron job to run every 10 days:
```bash
crontab -e
# Add this line (runs at 2 AM every 10 days):
0 2 */10 * * /path/to/process_latest.sh >> /path/to/logs/processing.log 2>&1
```

## Output Files

The script generates three files for each processed scene:

1. **`*_bathymetry.tif`** - Full resolution bathymetry raster
2. **`*_clipped.tif`** - Bathymetry clipped to your AOI
3. **`*.png`** - Visualization image ready for web display

## Methodology

### Band Ratio Technique

The script uses the log-ratio method for deriving relative bathymetry:

```
Relative Depth = ln(Green Band) / ln(Red Band)
```

This ratio is sensitive to water depth in shallow nearshore environments where:
- Deeper water absorbs more red light
- Shallower water reflects more red light
- The ratio reveals relative depth variations

### Why This Works for Rip Currents

Rip currents often flow through deeper channels between sandbars. The bathymetry map reveals:
- Lighter areas = shallower (sandbars)
- Darker areas = deeper (channels where rips form)
- Linear dark features = channelized rip current pathways

## Troubleshooting

### No products found
- Check your AOI covers Port Stanley
- Expand date range
- Increase `--max-cloud` parameter

### GDAL errors
- Ensure GDAL is properly installed
- Check that Python GDAL bindings match your GDAL version

### Band files not found
- Script expects Sentinel-2 Level-2A products (atmospherically corrected)
- Check that the SAFE directory structure is intact

## Advanced Customization

To modify the band ratio calculation, edit the `calculate_bathymetry_ratio()` method in `sentinel_bathymetry.py`:

```python
# Try blue/green ratio instead
bathymetry = np.log(blue) / np.log(green)
```

To adjust visualization:
- Change colormap: edit `cmap` parameter in `create_visualization()`
- Adjust DPI: modify `dpi` parameter in `plt.savefig()`

## References

- Stumpf, R. P., et al. (2003). "Determination of water depth with high-resolution satellite imagery over variable bottom types." *Limnology and Oceanography*, 48(1part2), 547-556.
- Lyzenga, D. R. (1978). "Passive remote sensing techniques for mapping water depth and bottom features." *Applied optics*, 17(3), 379-383.

## License

MIT License - feel free to use and modify for your lifeguarding operations!

## Contributing

This is an open-source project for beach safety. Contributions welcome:
- Improved band ratio algorithms
- Additional water quality parameters
- Better rip current identification
- Multi-temporal change detection
