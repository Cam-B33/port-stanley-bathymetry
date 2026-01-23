# RIP CURRENT FLOW VISUALIZATION

You asked for it, so I built it! Your website now has an animated flow visualization showing how water moves based on the bathymetry.

## What It Does

- **Animated particles** that flow along rip current paths
- **Three modes:**
  - **East Current** - Shows flow during easterly winds/currents
  - **West Current** - Shows flow during westerly winds/currents  
  - **Offshore Flow** - Shows perpendicular flow (classic rip current)
- **Toggle control** in the top-right of the map
- **Color-coded particles** that fade in/out as they flow
- **Trail effects** showing direction and speed

## How to Install

### Step 1: Update Your Website

Download `index_with_flow.html` and replace your current `index.html`:

```bash
cd /home/cameron/Dropbox/Port_Stanley_Bathymetry_2/website-package

# Backup current version
cp index.html index_backup.html

# Replace with flow version (after downloading)
# mv ~/Downloads/index_with_flow.html index.html

git add index.html
git commit -m "Add animated rip current flow visualization"
git push
```

### Step 2: Test It Out

1. Go to your website (wait 2 min for GitHub Pages to update)
2. Look for the **"Rip Current Flow"** control panel (top-right)
3. Select **"East Current"**, **"West Current"**, or **"Offshore Flow"**
4. Watch the animated particles show water movement!

## How It Works

The animation uses:
- **Particle system** - Hundreds of small animated dots
- **Flow calculations** - Based on your bathymetry overlay bounds
- **HTML5 Canvas** - Smooth 60fps animation overlay
- **Leaflet integration** - Synced with map zoom/pan

The flow directions are simplified right now:
- **East** = Particles move east (longshore current)
- **West** = Particles move west (longshore current)
- **Offshore** = Particles move perpendicular to shore (rip current)

## Advanced: Use Real Bathymetry Gradients (Optional)

Want even more accurate flow? Run this Python script to calculate actual flow vectors from depth gradients:

```bash
python generate_flow_data.py \
    --bathymetry port_bathymetry_CLI/output/port_stanley_sept_30_2024_clipped.tif \
    --output-dir website-package/js
```

This will generate `flow_vectors.json` with mathematically calculated flow directions based on where water naturally flows (shallow → deep).

Then update the JavaScript to load and use these vectors instead of the simplified directions.

## Customization Options

### Change Particle Color

In `index.html`, find this line:
```javascript
flowCtx.fillStyle = `rgba(255, 100, 100, ${this.opacity * 0.8})`;
```

Change RGB values:
- Red particles: `rgba(255, 100, 100, ...)`
- Blue particles: `rgba(100, 150, 255, ...)`
- Yellow particles: `rgba(255, 255, 100, ...)`

### Adjust Particle Density

Find this line:
```javascript
const latStep = (bathyBounds.north - bathyBounds.south) / 15;
const lonStep = (bathyBounds.east - bathyBounds.west) / 25;
```

Make numbers **larger** = fewer particles (faster)
Make numbers **smaller** = more particles (cooler but slower)

### Change Flow Speed

Find:
```javascript
this.speed = 0.0001 + Math.random() * 0.0001;
```

Increase these numbers to make particles move faster.

### Add More Flow Modes

Want to add "Northeast" or "Circular" patterns? Add new radio buttons and new cases in the particle update function!

## What People Will See

When visitors select a flow mode:
1. Hundreds of red particles appear over the bathymetry
2. They animate smoothly showing water flow direction
3. Particles fade in/out naturally
4. Works on mobile and desktop
5. Updates when they zoom/pan the map

This is genuinely useful AND looks really slick. Great idea!

## Next Enhancements

If you want to go further:
- Load actual flow vectors from the Python script (more accurate)
- Add wind direction input to show current flow patterns
- Color particles by flow speed (fast = red, slow = blue)
- Add historical rip current incident markers
- Create time-lapse of seasonal changes

Let me know what you want to add next!
