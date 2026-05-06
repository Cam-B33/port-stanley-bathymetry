#!/usr/bin/env python3
"""
Setup PostGIS Database Schema for Port Stanley Bathymetry
Creates tables optimized for spatial-temporal analysis
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Database connection
DB_CONFIG = {
    'dbname': 'port_stanley_bathymetry',
    'user': 'bathymetry_user',
    'password': 'changeme123',
    'host': 'localhost'
}

SCHEMA = """
-- ============================================================================
-- SCENES: Metadata about each Sentinel-2 acquisition
-- ============================================================================
CREATE TABLE IF NOT EXISTS scenes (
    id SERIAL PRIMARY KEY,
    scene_name VARCHAR(255) UNIQUE NOT NULL,
    acquisition_date DATE NOT NULL,
    acquisition_time TIME,
    satellite VARCHAR(10),
    tile_id VARCHAR(10),
    cloud_cover FLOAT,
    processing_date TIMESTAMP DEFAULT NOW(),
    quality VARCHAR(20),
    notes TEXT
);

CREATE INDEX idx_scenes_date ON scenes(acquisition_date);
CREATE INDEX idx_scenes_quality ON scenes(quality);

-- ============================================================================
-- BATHYMETRY_RASTERS: Store full raster metadata
-- ============================================================================
CREATE TABLE IF NOT EXISTS bathymetry_rasters (
    id SERIAL PRIMARY KEY,
    scene_id INTEGER REFERENCES scenes(id),
    file_path TEXT NOT NULL,
    min_depth FLOAT,
    max_depth FLOAT,
    mean_depth FLOAT,
    std_depth FLOAT,
    valid_pixels INTEGER,
    bounds GEOMETRY(POLYGON, 4326),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_rasters_scene ON bathymetry_rasters(scene_id);
CREATE INDEX idx_rasters_bounds ON bathymetry_rasters USING GIST(bounds);

-- ============================================================================
-- BATHYMETRY_POINTS: Gridded depth points for spatial queries
-- ============================================================================
CREATE TABLE IF NOT EXISTS bathymetry_points (
    id SERIAL PRIMARY KEY,
    scene_id INTEGER REFERENCES scenes(id),
    location GEOMETRY(POINT, 4326) NOT NULL,
    depth FLOAT NOT NULL,
    gradient_x FLOAT,
    gradient_y FLOAT,
    gradient_magnitude FLOAT,
    grid_x INTEGER,
    grid_y INTEGER
);

CREATE INDEX idx_points_scene ON bathymetry_points(scene_id);
CREATE INDEX idx_points_location ON bathymetry_points USING GIST(location);
CREATE INDEX idx_points_depth ON bathymetry_points(depth);
CREATE INDEX idx_points_gradient ON bathymetry_points(gradient_magnitude);

-- ============================================================================
-- DEPTH_CONTOURS: Contour lines for each depth interval
-- ============================================================================
CREATE TABLE IF NOT EXISTS depth_contours (
    id SERIAL PRIMARY KEY,
    scene_id INTEGER REFERENCES scenes(id),
    depth_value FLOAT NOT NULL,
    contour GEOMETRY(MULTILINESTRING, 4326) NOT NULL,
    length_meters FLOAT
);

CREATE INDEX idx_contours_scene ON depth_contours(scene_id);
CREATE INDEX idx_contours_depth ON depth_contours(depth_value);
CREATE INDEX idx_contours_geom ON depth_contours USING GIST(contour);

-- ============================================================================
-- RIP_RISK_ZONES: High-risk areas for rip currents
-- ============================================================================
CREATE TABLE IF NOT EXISTS rip_risk_zones (
    id SERIAL PRIMARY KEY,
    scene_id INTEGER REFERENCES scenes(id),
    flow_mode VARCHAR(20) NOT NULL, -- 'east', 'west', 'offshore'
    risk_level FLOAT NOT NULL,
    zone_geom GEOMETRY(POINT, 4326) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_rip_scene ON rip_risk_zones(scene_id);
CREATE INDEX idx_rip_mode ON rip_risk_zones(flow_mode);
CREATE INDEX idx_rip_level ON rip_risk_zones(risk_level);
CREATE INDEX idx_rip_geom ON rip_risk_zones USING GIST(zone_geom);

-- ============================================================================
-- SWIM_ZONE: Designated swimming area (static)
-- ============================================================================
CREATE TABLE IF NOT EXISTS swim_zone (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    zone_geom GEOMETRY(POLYGON, 4326) NOT NULL,
    active_from DATE,
    active_to DATE
);

CREATE INDEX idx_swim_geom ON swim_zone USING GIST(zone_geom);

-- Insert Port Stanley swim zone
INSERT INTO swim_zone (name, zone_geom, active_from) VALUES (
    'Port Stanley Main Beach',
    ST_GeomFromText('POLYGON((
        -81.21593214409477 42.658712889533405,
        -81.22060991661222 42.65995506200763,
        -81.22060991661222 42.658607595245144,
        -81.21593214409477 42.657365422770916,
        -81.21593214409477 42.658712889533405
    ))', 4326),
    '2024-01-01'
);

-- ============================================================================
-- LIFEGUARD_TOWERS: Tower locations (static)
-- ============================================================================
CREATE TABLE IF NOT EXISTS lifeguard_towers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50),
    location GEOMETRY(POINT, 4326) NOT NULL,
    tower_type VARCHAR(20),
    active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_towers_location ON lifeguard_towers USING GIST(location);

-- Insert Port Stanley towers
INSERT INTO lifeguard_towers (name, location, tower_type) VALUES
    ('Tower 1', ST_GeomFromText('POINT(-81.21593214409477 42.658712889533405)', 4326), 'standard'),
    ('Tower 2', ST_GeomFromText('POINT(-81.21743552224498 42.65912810039798)', 4326), 'standard'),
    ('Central Tower', ST_GeomFromText('POINT(-81.21815435426022 42.65961530391666)', 4326), 'main'),
    ('Tower 3', ST_GeomFromText('POINT(-81.21897376911585 42.65954281537943)', 4326), 'standard'),
    ('Tower 4', ST_GeomFromText('POINT(-81.22060991661222 42.65995506200763)', 4326), 'standard');

-- ============================================================================
-- TEMPORAL_CHANGES: Track depth changes between consecutive scenes
-- ============================================================================
CREATE TABLE IF NOT EXISTS temporal_changes (
    id SERIAL PRIMARY KEY,
    scene_id_before INTEGER REFERENCES scenes(id),
    scene_id_after INTEGER REFERENCES scenes(id),
    location GEOMETRY(POINT, 4326) NOT NULL,
    depth_before FLOAT,
    depth_after FLOAT,
    depth_change FLOAT,
    change_rate FLOAT, -- meters per day
    days_elapsed INTEGER
);

CREATE INDEX idx_changes_location ON temporal_changes USING GIST(location);
CREATE INDEX idx_changes_magnitude ON temporal_changes(ABS(depth_change));

-- ============================================================================
-- ANALYSIS_QUERIES: Save useful queries for reuse
-- ============================================================================
CREATE TABLE IF NOT EXISTS saved_queries (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    sql_query TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- VIEWS: Pre-computed common queries
-- ============================================================================

-- Latest bathymetry data
CREATE OR REPLACE VIEW latest_bathymetry AS
SELECT 
    s.acquisition_date,
    s.scene_name,
    bp.location,
    bp.depth,
    bp.gradient_magnitude
FROM bathymetry_points bp
JOIN scenes s ON bp.scene_id = s.id
WHERE s.acquisition_date = (SELECT MAX(acquisition_date) FROM scenes);

-- Persistent rip zones (appears in 3+ scenes)
CREATE OR REPLACE VIEW persistent_rip_zones AS
SELECT 
    ST_Centroid(ST_Union(zone_geom)) as location,
    flow_mode,
    COUNT(*) as frequency,
    AVG(risk_level) as avg_risk
FROM rip_risk_zones
GROUP BY flow_mode, ST_SnapToGrid(zone_geom, 0.0001)
HAVING COUNT(*) >= 3;

-- Depth statistics by zone
CREATE OR REPLACE VIEW swim_zone_stats AS
SELECT 
    s.acquisition_date,
    COUNT(*) as point_count,
    AVG(bp.depth) as avg_depth,
    MIN(bp.depth) as min_depth,
    MAX(bp.depth) as max_depth,
    STDDEV(bp.depth) as std_depth
FROM bathymetry_points bp
JOIN scenes s ON bp.scene_id = s.id
JOIN swim_zone sz ON ST_Within(bp.location, sz.zone_geom)
GROUP BY s.acquisition_date
ORDER BY s.acquisition_date;

"""

def setup_database():
    """Create all tables and indexes."""
    print("Setting up Port Stanley Bathymetry Database Schema...")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Execute schema
        cursor.execute(SCHEMA)
        
        # Verify PostGIS
        cursor.execute("SELECT PostGIS_Version();")
        version = cursor.fetchone()[0]
        print(f"✓ PostGIS Version: {version}")
        
        # Count tables
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """)
        table_count = cursor.fetchone()[0]
        print(f"✓ Created {table_count} tables")
        
        # Count views
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.views 
            WHERE table_schema = 'public'
        """)
        view_count = cursor.fetchone()[0]
        print(f"✓ Created {view_count} views")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Database schema ready!")
        print("\nNext steps:")
        print("1. python3 load_bathymetry_data.py  # Import your GeoTIFFs")
        print("2. jupyter notebook analysis/        # Start exploring!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise

if __name__ == "__main__":
    setup_database()
