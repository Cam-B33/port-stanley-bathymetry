#!/bin/bash
#
# Website Setup Script
# Initializes the website directory structure and copies necessary files
#

set -e

echo "================================================"
echo "Port Stanley Bathymetry Website Setup"
echo "================================================"
echo ""

# Create website directory structure
echo "Creating website directory structure..."
mkdir -p website/maps
mkdir -p website/css
mkdir -p website/js

# Copy main HTML file
echo "Copying website files..."
cp index.html website/

# Initialize empty maps data
echo "Initializing maps data..."
cat > website/maps_data.json << 'EOF'
{
  "maps": [],
  "latest": null
}
EOF

cat > website/maps_data.js << 'EOF'
const mapsData = {
  "maps": [],
  "latest": null
};
EOF

echo ""
echo "================================================"
echo "Website setup complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Add your first map:"
echo "   python update_website.py \\"
echo "       --add output/your_map.png \\"
echo "       --date 2024-09-30 \\"
echo "       --description 'Initial bathymetry map'"
echo ""
echo "2. Test locally:"
echo "   cd website"
echo "   python -m http.server 8000"
echo "   Open http://localhost:8000"
echo ""
echo "3. Deploy to GitHub Pages:"
echo "   cd website"
echo "   git init"
echo "   git add ."
echo "   git commit -m 'Initial website'"
echo "   git remote add origin https://github.com/USERNAME/REPO.git"
echo "   git push -u origin main"
echo ""
echo "4. Or deploy to Netlify:"
echo "   Drag and drop the 'website' folder to netlify.com"
echo ""
