# Bathymetry Maps

This folder contains the bathymetry map images displayed on the website.

Maps are added using the `update_website.py` script:

```bash
python update_website.py \
    --add ../output/your_map.png \
    --date 2024-09-30 \
    --description "Description of conditions"
```

Each map should be a PNG file named: `bathymetry_YYYY_MM_DD.png`
