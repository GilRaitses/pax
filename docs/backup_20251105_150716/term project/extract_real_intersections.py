#!/usr/bin/env python3
"""Extract REAL intersection points from NYC street centerline data"""

import json
import numpy as np
from shapely.geometry import LineString, Point
from shapely.ops import unary_union
import matplotlib.pyplot as plt
from scipy.spatial import Voronoi

print("Loading street centerlines...")
with open('manhattan_streets.geojson', 'r') as f:
    streets_data = json.load(f)

# Filter streets in corridor
corridor_streets = []
for feature in streets_data['features']:
    if feature['geometry']['type'] == 'LineString':
        coords = feature['geometry']['coordinates']
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        
        # Only streets in corridor
        if (any(40.745 <= lat <= 40.772 for lat in lats) and
            any(-74.002 <= lon <= -73.968 for lon in lons)):
            corridor_streets.append(LineString(coords))

print(f"Street segments in corridor: {len(corridor_streets)}")

# Find real intersections by checking where lines cross
print("Computing actual intersection points...")
real_intersections = []
intersection_coords = set()

for i, street1 in enumerate(corridor_streets):
    for street2 in corridor_streets[i+1:]:
        try:
            if street1.intersects(street2):
                intersection = street1.intersection(street2)
                if intersection.geom_type == 'Point':
                    coord = (round(intersection.x, 6), round(intersection.y, 6))
                    if coord not in intersection_coords:
                        # Filter to corridor bounds
                        if (40.745 <= intersection.y <= 40.772 and
                            -74.002 <= intersection.x <= -73.968):
                            intersection_coords.add(coord)
                            real_intersections.append([intersection.x, intersection.y])
        except:
            pass
    
    if (i + 1) % 10 == 0:
        print(f"  Processed {i+1}/{len(corridor_streets)} streets, found {len(real_intersections)} intersections so far...")

real_intersections = np.array(real_intersections)
print(f"\nREAL intersections found: {len(real_intersections)}")

# Save for later use
with open('real_intersections.json', 'w') as f:
    json.dump(real_intersections.tolist(), f)
    
print(f"Saved to real_intersections.json")
print(f"\nThis is the ACTUAL state space size, not a made-up grid!")

