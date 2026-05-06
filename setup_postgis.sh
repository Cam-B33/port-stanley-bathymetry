#!/bin/bash
# Setup PostgreSQL + PostGIS for Port Stanley Bathymetry Analysis

echo "=================================="
echo "Setting up PostGIS Database"
echo "=================================="

# Install PostgreSQL and PostGIS
echo "Installing PostgreSQL and PostGIS..."
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib postgis

# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
echo "Creating database..."
sudo -u postgres psql << EOF
CREATE DATABASE port_stanley_bathymetry;
\c port_stanley_bathymetry
CREATE EXTENSION postgis;
CREATE EXTENSION postgis_topology;

-- Create user
CREATE USER bathymetry_user WITH PASSWORD 'changeme123';
GRANT ALL PRIVILEGES ON DATABASE port_stanley_bathymetry TO bathymetry_user;
GRANT ALL ON ALL TABLES IN SCHEMA public TO bathymetry_user;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO bathymetry_user;

-- Verify PostGIS
SELECT PostGIS_Version();
EOF

echo ""
echo "✓ Database created: port_stanley_bathymetry"
echo "✓ PostGIS enabled"
echo "✓ User: bathymetry_user"
echo ""
echo "Next: python3 setup_schema.py"
