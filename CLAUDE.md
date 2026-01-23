# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Port Stanley Bathymetry - A Python/web system that processes Sentinel-2 satellite imagery to generate bathymetry maps (underwater depth visualization) of Port Stanley, Ontario beach, with interactive visualization and animated rip current flow simulation for beach safety.

## Architecture

### Three Main Components

1. **CLI Processing Engine** (`port_bathymetry_CLI/`)
   - Core: `sentinel_bathymetry.py` - `SentinelBathymetryProcessor` class
   - Downloads Sentinel-2 imagery from Copernicus Hub
   - Calculates bathymetry using band ratio: `ln(Green)/ln(Red)`
   - Outputs: GeoTIFF rasters, PNG visualizations, optional shapefiles

2. **Website** (`docs/`)
   - Static site deployed to GitHub Pages
   - `index.html` contains embedded CSS/JS with Leaflet.js mapping
   - Particle-based flow animation for rip current visualization
   - Data: `maps_data.json` tracks published bathymetry maps

3. **Data Utilities** (root directory)
   - `update_website.py` - Adds new maps to website
   - `generate_flow_data.py` - Calculates flow vectors from bathymetry gradients
   - `generate_rip_heatmap.py` - Risk zone analysis using divergence

## Commands

### Setup
```bash
python port_bathymetry_CLI/check_setup.py
pip install -r port_bathymetry_CLI/requirements.txt
cp port_bathymetry_CLI/config_template.py port_bathymetry_CLI/config.py
# Edit config.py with Copernicus credentials
```

### Process Local Sentinel-2 Data
```bash
python port_bathymetry_CLI/sentinel_bathymetry.py process \
    --scene /path/to/S2A_MSIL2A_*.SAFE \
    --aoi port_bathymetry_CLI/aoi.geojson \
    --output output_name
```

### Download and Process (Automated)
```bash
python port_bathymetry_CLI/sentinel_bathymetry.py download-and-process \
    --aoi port_bathymetry_CLI/aoi.geojson \
    --start-date 20240601 \
    --end-date 20240610 \
    --username <copernicus_user> \
    --password <copernicus_pass> \
    --max-cloud 20
```

### Publish to Website
```bash
python update_website.py \
    --add port_bathymetry_CLI/output/bathymetry_2024_06_10.png \
    --date 2024-06-10 \
    --description "Post-storm conditions" \
    --website-dir docs

cd docs && git add . && git commit -m "Add map" && git push
```

### Flow Analysis
```bash
python generate_flow_data.py \
    --bathymetry port_bathymetry_CLI/output/port_stanley_clipped.tif \
    --output-dir docs/maps

python generate_rip_heatmap.py \
    --bathymetry port_bathymetry_CLI/output/port_stanley_clipped.tif \
    --output docs/maps/rip_risk_zones.json
```

## Tech Stack

**Processing:** Python 3.8+, rasterio, GDAL, numpy, sentinelsat, matplotlib, scipy

**Web:** HTML5, Leaflet.js 1.9.4, HTML5 Canvas (particle animation)

**Deployment:** GitHub Pages at `docs/` subdirectory (separate git repo)

## Key Files

- `port_bathymetry_CLI/sentinel_bathymetry.py` - Main processor (SentinelBathymetryProcessor class)
- `port_bathymetry_CLI/aoi.geojson` - Area of interest polygon for Port Stanley beach
- `docs/index.html` - Interactive map with flow animation
- `docs/maps_data.json` - Published maps metadata
- `update_website.py` - Automation for adding new maps

## Scientific Background

Band ratio bathymetry: Deeper water absorbs more red light, shallower water reflects more. The `ln(Green)/ln(Red)` ratio reveals relative depth - sandbars appear lighter, channels darker, rip pathways as linear dark features.

Flow analysis calculates bathymetry gradients to identify convergence zones (negative divergence = rip currents).

## Notes

- Virtual environment exists at `venv/`
- Processing outputs go to `port_bathymetry_CLI/output/`
- Website repo is separate from main project (only `docs/` is git-tracked)
- Copernicus credentials required in `config.py` (not committed)
