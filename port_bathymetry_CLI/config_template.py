# Configuration file for Sentinel-2 Bathymetry Processing
# Copy this to config.py and fill in your credentials

# Copernicus Open Access Hub credentials
# Register at: https://scihub.copernicus.eu/dhus/#/self-registration
COPERNICUS_USERNAME = "your_username_here"
COPERNICUS_PASSWORD = "your_password_here"

# Area of Interest
AOI_GEOJSON = "aoi.geojson"

# Processing parameters
MAX_CLOUD_COVER = 20  # Maximum cloud cover percentage (0-100)

# Output directories
OUTPUT_DIR = "output"
TEMP_DIR = "temp"

# Visualization settings
COLORMAP = "viridis_r"  # Options: viridis_r, Blues_r, YlGnBu_r, ocean_r
DPI = 300  # Resolution for output images

# Processing settings
BAND_RATIO_METHOD = "green_red"  # Options: green_red, blue_green
