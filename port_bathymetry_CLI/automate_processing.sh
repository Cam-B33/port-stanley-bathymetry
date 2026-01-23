#!/bin/bash
#
# Automated Sentinel-2 Processing Script
# Runs processing for the last 10 days of imagery
#
# Usage: ./automate_processing.sh
# Or set up as a cron job: 0 2 */10 * * /path/to/automate_processing.sh

set -e  # Exit on error

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Load credentials from config or environment variables
if [ -f "config.py" ]; then
    source <(grep -E '^(COPERNICUS_USERNAME|COPERNICUS_PASSWORD|AOI_GEOJSON)' config.py | sed 's/ = /=/g' | sed 's/"//g')
elif [ -z "$COPERNICUS_USER" ] || [ -z "$COPERNICUS_PASS" ]; then
    echo "Error: Credentials not found. Set COPERNICUS_USER and COPERNICUS_PASS environment variables"
    exit 1
fi

# Use environment variables if config.py didn't set them
USERNAME="${COPERNICUS_USERNAME:-$COPERNICUS_USER}"
PASSWORD="${COPERNICUS_PASSWORD:-$COPERNICUS_PASS}"
AOI="${AOI_GEOJSON:-aoi.geojson}"

# Calculate date range
END_DATE=$(date +%Y%m%d)
START_DATE=$(date -d "10 days ago" +%Y%m%d)

echo "================================================"
echo "Sentinel-2 Automated Processing"
echo "================================================"
echo "Date range: $START_DATE to $END_DATE"
echo "AOI: $AOI"
echo "Starting: $(date)"
echo "================================================"

# Create logs directory if it doesn't exist
mkdir -p logs

# Run processing
python sentinel_bathymetry.py download-and-process \
    --aoi "$AOI" \
    --start-date "$START_DATE" \
    --end-date "$END_DATE" \
    --username "$USERNAME" \
    --password "$PASSWORD" \
    --max-cloud 20 \
    2>&1 | tee "logs/processing_$(date +%Y%m%d_%H%M%S).log"

echo "================================================"
echo "Processing complete: $(date)"
echo "================================================"

# Optional: Clean up temp files older than 30 days
find temp -name "*.SAFE" -type d -mtime +30 -exec rm -rf {} + 2>/dev/null || true

echo "Check output/ directory for results"
