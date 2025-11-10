#!/usr/bin/env python3
"""Compute actual street intersections where two different streets cross"""

import geopandas as gpd
import numpy as np
import json
from shapely.geometry import Point
from shapely.ops import unary_union

print("Loading NYC Planning Digital City Map...")
dcm = gpd.read_file('DCM_StreetCenterLine.shp')
dcm_latlon = dcm.to_crs(epsg=4326)
manhattan = dcm_latlon[dcm_latlon['Borough'] == 'Manhattan'].copy()

# Filter corridor streets
print("Filtering corridor streets...")
corridor_streets = []
for idx, row in manhattan.iterrows():
    bounds = row.geometry.bounds
    if not (bounds[2] < -74.002 or bounds[0] > -73.968 or
            bounds[3] < 40.745 or bounds[1] > 40.772):
        corridor_streets.append(row)

corridor = gpd.GeoDataFrame(corridor_streets, crs='EPSG:4326')
print(f"Corridor streets: {len(corridor)}")

# Find actual intersections where streets cross
print("Computing actual intersections (this may take a moment)...")
intersections = {}
checked_pairs = set()

for i, row1 in corridor.iterrows():
    street1 = row1['Street_NM']
    geom1 = row1.geometry
    
    for j, row2 in corridor.iterrows():
        if i >= j:  # Skip self and already-checked pairs
            continue
            
        street2 = row2['Street_NM']
        
        # Only check if different streets
        if street1 != street2:
            pair = tuple(sorted([street1, street2]))
            if pair in checked_pairs:
                continue
            checked_pairs.add(pair)
            
            geom2 = row2.geometry
            
            # Check if they intersect
            if geom1.intersects(geom2):
                try:
                    intersection = geom1.intersection(geom2)
                    
                    # Handle different intersection types
                    if intersection.geom_type == 'Point':
                        lon, lat = intersection.x, intersection.y
                        if (40.745 <= lat <= 40.772 and -74.002 <= lon <= -73.968):
                            key = (round(lon, 5), round(lat, 5))
                            if key not in intersections:
                                intersections[key] = {
                                    'coord': (lon, lat),
                                    'streets': [street1, street2]
                                }
                    
                    elif intersection.geom_type == 'MultiPoint':
                        for point in intersection.geoms:
                            lon, lat = point.x, point.y
                            if (40.745 <= lat <= 40.772 and -74.002 <= lon <= -73.968):
                                key = (round(lon, 5), round(lat, 5))
                                if key not in intersections:
                                    intersections[key] = {
                                        'coord': (lon, lat),
                                        'streets': [street1, street2]
                                    }
                except Exception as e:
                    pass
    
    if (len(corridor) - i) % 50 == 0:
        print(f"  Processed {i}/{len(corridor)} streets, found {len(intersections)} intersections...")

print(f"\nACTUAL intersections (where streets cross): {len(intersections)}")

# Extract coordinates
intersection_coords = np.array([data['coord'] for data in intersections.values()])

# Save
with open('actual_intersections.json', 'w') as f:
    json.dump({
        'count': len(intersections),
        'coordinates': intersection_coords.tolist(),
        'intersections': {str(k): v for k, v in intersections.items()}
    }, f, indent=2)

print(f"Saved to actual_intersections.json")
print(f"\nThis is the correct state space size!")
print(f"Sample intersections:")
for i, (key, data) in enumerate(list(intersections.items())[:5]):
    print(f"  {data['streets'][0]} × {data['streets'][1]}: {data['coord']}")

