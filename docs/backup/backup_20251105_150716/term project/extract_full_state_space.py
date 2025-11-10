#!/usr/bin/env python3
"""Extract complete state space from NYC Planning shapefile"""

import geopandas as gpd
import numpy as np
import json
from shapely.geometry import Point

print("="*70)
print("EXTRACTING REAL STATE SPACE FROM NYC PLANNING DATA")
print("="*70)

# Load DCM shapefile
print("\n1. Loading NYC Planning DCM Street Centerline Shapefile...")
dcm = gpd.read_file('DCM_StreetCenterLine.shp')
print(f"   Total citywide streets: {len(dcm)}")
print(f"   CRS: {dcm.crs} (NY State Plane - feet)")

# Convert to lat/lon for easier filtering
dcm_latlon = dcm.to_crs(epsg=4326)

# Filter Manhattan
manhattan = dcm_latlon[dcm_latlon['Borough'] == 'Manhattan'].copy()
print(f"   Manhattan streets: {len(manhattan)}")

# Filter corridor
print("\n2. Filtering corridor (40th-59th St, Lex-8th Ave)...")
corridor_streets = []
for idx, row in manhattan.iterrows():
    bounds = row.geometry.bounds
    # Check overlap
    if not (bounds[2] < -74.002 or bounds[0] > -73.968 or
            bounds[3] < 40.745 or bounds[1] > 40.772):
        corridor_streets.append(row)

corridor = gpd.GeoDataFrame(corridor_streets, crs='EPSG:4326')
print(f"   Corridor streets: {len(corridor)}")

# Extract intersection points
print("\n3. Extracting real intersection coordinates...")
intersection_coords = set()
for idx, row in corridor.iterrows():
    geom = row.geometry
    if geom.geom_type == 'LineString':
        for coord in geom.coords:
            lon, lat = coord[0], coord[1]
            if (40.745 <= lat <= 40.772 and -74.002 <= lon <= -73.968):
                intersection_coords.add((round(lon, 5), round(lat, 5)))
    elif geom.geom_type == 'MultiLineString':
        for line in geom.geoms:
            for coord in line.coords:
                lon, lat = coord[0], coord[1]
                if (40.745 <= lat <= 40.772 and -74.002 <= lon <= -73.968):
                    intersection_coords.add((round(lon, 5), round(lat, 5)))

real_intersections = np.array(list(intersection_coords))
print(f"   Real intersections: {len(real_intersections)}")

# Load and filter cameras
print("\n4. Loading NYC DOT cameras...")
with open('nyc_cameras_full.json', 'r') as f:
    all_cameras = json.load(f)

corridor_cameras = []
for cam in all_cameras:
    try:
        lat = float(cam['latitude'])
        lon = float(cam['longitude'])
        if (cam.get('area') == 'Manhattan' and 
            40.745 <= lat <= 40.772 and 
            -74.002 <= lon <= -73.968):
            corridor_cameras.append(cam)
    except:
        pass

print(f"   Corridor cameras: {len(corridor_cameras)}")

# Save
print("\n5. Saving data...")
with open('real_intersections_final.json', 'w') as f:
    json.dump(real_intersections.tolist(), f)

corridor.to_file('corridor_streets_final.geojson', driver='GeoJSON')

print("="*70)
print("FINAL STATE SPACE:")
print(f"  States (intersections): {len(real_intersections)}")
print(f"  Camera zones: {len(corridor_cameras)}")
print(f"  Ratio: {len(real_intersections)/len(corridor_cameras):.2f} intersections per camera")
print("="*70)
print(f"\nData source: NYC Planning Digital City Map (June 2025)")
print(f"Camera source: NYC DOT Traffic Management Center API")
EOF

