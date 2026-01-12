#!/usr/bin/env python3
"""
Website Update Script
Automatically updates the website with new bathymetry maps
"""

import json
import shutil
from pathlib import Path
from datetime import datetime

class WebsiteUpdater:
    def __init__(self, website_dir="website", output_dir="output"):
        self.website_dir = Path(website_dir)
        self.output_dir = Path(output_dir)
        self.maps_dir = self.website_dir / "maps"
        self.maps_dir.mkdir(parents=True, exist_ok=True)
        
        # Data file to track all maps
        self.data_file = self.website_dir / "maps_data.json"
        self.load_data()
    
    def load_data(self):
        """Load existing maps data."""
        if self.data_file.exists():
            with open(self.data_file, 'r') as f:
                self.maps_data = json.load(f)
        else:
            self.maps_data = {
                'maps': [],
                'latest': None
            }
    
    def save_data(self):
        """Save maps data."""
        with open(self.data_file, 'w') as f:
            json.dump(self.maps_data, f, indent=2)
    
    def add_map(self, bathymetry_png, date_str, description=""):
        """
        Add a new bathymetry map to the website.
        
        Args:
            bathymetry_png: Path to the bathymetry PNG image
            date_str: Date string (YYYY-MM-DD)
            description: Optional description of conditions
        """
        bathymetry_png = Path(bathymetry_png)
        
        if not bathymetry_png.exists():
            print(f"Error: {bathymetry_png} not found")
            return False
        
        # Create filename
        safe_date = date_str.replace('-', '_')
        dest_filename = f"bathymetry_{safe_date}.png"
        dest_path = self.maps_dir / dest_filename
        
        # Copy file
        shutil.copy(bathymetry_png, dest_path)
        print(f"Copied {bathymetry_png} -> {dest_path}")
        
        # Add to data
        map_entry = {
            'filename': dest_filename,
            'date': date_str,
            'description': description,
            'added': datetime.now().isoformat()
        }
        
        self.maps_data['maps'].append(map_entry)
        self.maps_data['latest'] = map_entry
        
        # Sort by date (newest first)
        self.maps_data['maps'].sort(key=lambda x: x['date'], reverse=True)
        
        self.save_data()
        print(f"Added map for {date_str}")
        
        return True
    
    def generate_maps_js(self):
        """Generate JavaScript file with maps data."""
        js_content = f"const mapsData = {json.dumps(self.maps_data, indent=2)};\n"
        
        js_file = self.website_dir / "maps_data.js"
        with open(js_file, 'w') as f:
            f.write(js_content)
        
        print(f"Generated {js_file}")
    
    def update_website(self):
        """Update website with latest data."""
        self.generate_maps_js()
        print("\nWebsite updated!")
        print(f"Total maps: {len(self.maps_data['maps'])}")
        if self.maps_data['latest']:
            print(f"Latest: {self.maps_data['latest']['date']}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Update website with new bathymetry maps'
    )
    
    parser.add_argument('--add', 
                       help='Path to bathymetry PNG to add')
    parser.add_argument('--date',
                       help='Date of the map (YYYY-MM-DD)')
    parser.add_argument('--description',
                       default='',
                       help='Optional description')
    parser.add_argument('--website-dir',
                       default='website',
                       help='Website directory (default: website)')
    parser.add_argument('--output-dir',
                       default='output',
                       help='Processing output directory (default: output)')
    
    args = parser.parse_args()
    
    updater = WebsiteUpdater(args.website_dir, args.output_dir)
    
    if args.add:
        if not args.date:
            print("Error: --date required when adding a map")
            return
        
        updater.add_map(args.add, args.date, args.description)
        updater.update_website()
    else:
        # Just regenerate JS from existing data
        updater.update_website()


if __name__ == "__main__":
    main()
