# Port Stanley Bathymetry - GitHub Pages Deployment

This folder contains everything you need to deploy your bathymetry mapping website to GitHub Pages.

## Quick Start Guide

### Step 1: Download This Folder

Download all files from this package to your local machine. You should have:

```
website-package/
├── index.html              # Main website
├── maps/                   # Folder for bathymetry images (empty initially)
├── css/                    # Folder for custom CSS (empty - using inline)
├── js/                     # Folder for custom JS (empty - using inline)
├── maps_data.json          # Map metadata (empty initially)
├── maps_data.js            # JavaScript data file (empty initially)
├── update_website.py       # Script to add new maps
├── setup_website.sh        # Setup script (optional)
└── README.md              # This file
```

### Step 2: Create GitHub Repository

1. Go to https://github.com and sign in
2. Click the **+** icon in top right → **New repository**
3. Name it: `port-stanley-bathymetry` (or whatever you prefer)
4. Make it **Public**
5. **DO NOT** initialize with README, .gitignore, or license
6. Click **Create repository**

### Step 3: Initialize Git and Push

Open terminal in the `website-package` folder and run:

```bash
# Initialize git repository
git init

# Add all files
git add .

# Commit
git commit -m "Initial website deployment"

# Add your GitHub repository as remote
git remote add origin https://github.com/Cam-B33/port-stanley-bathymetry.git

# Rename branch to main (if needed)
git branch -M main

# Push to GitHub
git push -u origin main
```

### Step 4: Enable GitHub Pages

1. Go to your repository on GitHub
2. Click **Settings** tab
3. Scroll down to **Pages** in the left sidebar
4. Under **Source**, select:
   - Branch: `main`
   - Folder: `/ (root)`
5. Click **Save**

**Your site will be live at:** `https://cam-b33.github.io/port-stanley-bathymetry/`

It may take 1-2 minutes to deploy. Refresh after a moment.

## Adding Your First Map

Once your site is live, add your first bathymetry map:

### Option 1: Using the Update Script (Recommended)

```bash
# Make sure you're in your project root (where sentinel_bathymetry.py is)
cd /path/to/your/project

# Add a map (this copies it to website-package/maps/)
python website-package/update_website.py \
    --add output/port_stanley_sept_30_2024.png \
    --date 2024-09-30 \
    --description "Clear rip channels visible on east side" \
    --website-dir website-package

# Commit and push the changes
cd website-package
git add .
git commit -m "Add September 30 bathymetry map"
git push
```

Your website will automatically update in 1-2 minutes!

### Option 2: Manual (Without Script)

1. Copy your bathymetry PNG to `website-package/maps/`
2. Name it: `bathymetry_YYYY_MM_DD.png` (e.g., `bathymetry_2024_09_30.png`)
3. Edit `maps_data.json` to add your map:

```json
{
  "maps": [
    {
      "filename": "bathymetry_2024_09_30.png",
      "date": "2024-09-30",
      "description": "Clear rip channels visible on east side",
      "added": "2024-09-30T12:00:00"
    }
  ],
  "latest": {
    "filename": "bathymetry_2024_09_30.png",
    "date": "2024-09-30",
    "description": "Clear rip channels visible on east side",
    "added": "2024-09-30T12:00:00"
  }
}
```

4. Update `maps_data.js` with the same data:

```javascript
const mapsData = {
  "maps": [
    {
      "filename": "bathymetry_2024_09_30.png",
      "date": "2024-09-30",
      "description": "Clear rip channels visible on east side",
      "added": "2024-09-30T12:00:00"
    }
  ],
  "latest": {
    "filename": "bathymetry_2024_09_30.png",
    "date": "2024-09-30",
    "description": "Clear rip channels visible on east side",
    "added": "2024-09-30T12:00:00"
  }
};
```

5. Commit and push:

```bash
cd website-package
git add .
git commit -m "Add first bathymetry map"
git push
```

## Regular Updates Throughout Summer

Every time you process new imagery:

```bash
# Process Sentinel-2 data
python sentinel_bathymetry.py process \
    --scene /path/to/sentinel_data \
    --aoi aoi.geojson \
    --output july_15_2024

# Add to website
python website-package/update_website.py \
    --add output/july_15_2024.png \
    --date 2024-07-15 \
    --description "Post-storm conditions" \
    --website-dir website-package

# Push to GitHub (updates website automatically)
cd website-package
git add .
git commit -m "Add July 15 bathymetry map"
git push
```

## Customizing Your Site

### Update Beach Information

Edit `index.html` and change:

- Line with "Port Stanley Main Beach" header
- Coordinates in the map initialization
- Swim zone polygon coordinates
- Lifeguard tower markers

### Change Colors

Find the CSS variables section in `index.html`:

```css
:root {
    --bg-primary: #fefefe;        /* Background color */
    --text-primary: #1a1a1a;      /* Text color */
    --accent: #2563eb;            /* Link color */
    --border: #ddd;               /* Border color */
}
```

### Add Georeferenced Overlay

To overlay your bathymetry map directly on the interactive map:

1. Find this section in `index.html` (search for "Placeholder for bathymetry overlay"):

```javascript
// Placeholder for bathymetry overlay
// In production, you would load your georeferenced bathymetry image here
```

2. Replace with:

```javascript
// Add your latest bathymetry map
const bathymetryBounds = [
    [42.648, -81.244],  // Southwest corner [lat, lon]
    [42.663, -81.212]   // Northeast corner [lat, lon]
];

L.imageOverlay('maps/bathymetry_2024_09_30.png', bathymetryBounds, {
    opacity: 0.7
}).addTo(map);
```

3. Adjust the bounds to match your actual map extent (check in QGIS)

### Add Lifeguard Towers

Find the marker section and add more:

```javascript
// Tower 1
L.marker([42.6665, -81.2180])
    .addTo(map)
    .bindPopup('<b>Tower 1</b><br>East station');

// Tower 2
L.marker([42.6655, -81.2165])
    .addTo(map)
    .bindPopup('<b>Tower 2</b><br>Central station');
```

### Update GitHub Link

Search for "github.com/yourusername" in `index.html` and replace with your actual repository URL.

## Testing Locally Before Pushing

```bash
cd website-package
python -m http.server 8000
# Open http://localhost:8000 in browser
```

Test everything works, then push to GitHub.

## File Size Considerations

- GitHub Pages has a 1GB repository size limit
- Individual files should be under 100MB
- Your bathymetry PNGs (at ~2-5MB each) are fine
- You can have 100+ maps without issues

## Troubleshooting

### Site not updating?

1. Check GitHub Actions tab in your repository - build should succeed
2. Wait 2-3 minutes after pushing
3. Hard refresh your browser (Ctrl+Shift+R or Cmd+Shift+R)
4. Check that files are actually on GitHub

### Images not showing?

1. Make sure images are in the `maps/` folder
2. Check filename matches what's in `maps_data.json`
3. Verify the file was pushed to GitHub
4. Check browser console for errors (F12)

### Map not centered correctly?

Adjust coordinates in this line:

```javascript
const map = L.map('map').setView([42.6666, -81.2169], 15);
//                                 ^latitude  ^longitude  ^zoom
```

## Directory Structure for Your Local Setup

Recommended organization:

```
port-stanley-bathymetry/
├── sentinel_bathymetry.py       # Processing script
├── requirements.txt              # Python dependencies
├── aoi.geojson                   # Your area of interest
├── output/                       # Processing outputs
│   ├── bathymetry_*.tif
│   └── bathymetry_*.png
└── website-package/              # THIS FOLDER - connected to GitHub
    ├── index.html
    ├── maps/
    │   └── bathymetry_*.png     # Maps copied here by update script
    └── maps_data.json
```

## Next Steps: Advanced Features

Once your basic site is running, you can add:

1. **Custom domain** - Point your own domain to GitHub Pages
2. **Analytics** - Add Google Analytics to track visitors
3. **Advanced overlays** - Use GeoTIFF tiles for better performance
4. **Animation** - Create time-lapse of bathymetry changes
5. **Weather integration** - Pull wave/wind data from APIs
6. **Mobile app** - Turn it into a PWA (Progressive Web App)

## Need Help?

- GitHub Pages docs: https://docs.github.com/en/pages
- Leaflet.js docs: https://leafletjs.com/
- Check your repository's Actions tab for build errors

---

**Remember:** After any changes to files, always:
```bash
git add .
git commit -m "Describe your changes"
git push
```

Your site updates automatically after each push!
