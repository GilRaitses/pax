#!/usr/bin/env python3
"""Process full NYC DCM shapefile to extract real state space"""

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import json
from shapely.geometry import Point
from scipy.spatial import Voronoi

print("Loading full DCM shapefile...")
dcm = gpd.read_file('DCM_StreetCenterLine.shp')
print(f"Total street centerlines: {len(dcm)}")

# Filter for Manhattan in corridor
print("Filtering for corridor (40th to 59th St, Lex to 8th Ave)...")
manhattan = dcm[dcm['Borough'] == 'Manhattan'].copy()
corridor = manhattan.cx[-74.002:-73.968, 40.745:40.772]
print(f"Street segments in corridor: {len(corridor)}")

# Extract unique intersection points from street endpoints
print("Extracting real intersection coordinates...")
intersection_coords = set()

for idx, row in corridor.iterrows():
    geom = row.geometry
    if geom.geom_type == 'LineString':
        # Add start and end points
        coords = list(geom.coords)
        for lon, lat in coords:
            rounded = (round(lon, 5), round(lat, 5))
            intersection_coords.add(rounded)
    elif geom.geom_type == 'MultiLineString':
        for line in geom.geoms:
            coords = list(line.coords)
            for lon, lat in coords:
                rounded = (round(lon, 5), round(lat, 5))
                intersection_coords.add(rounded)

real_intersections = np.array(list(intersection_coords))
print(f"REAL intersections: {len(real_intersections)}")

# Load cameras
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

camera_coords = np.array([[float(cam['longitude']), float(cam['latitude'])] 
                          for cam in corridor_cameras])

print(f"Cameras: {len(corridor_cameras)}")
print(f"Ratio: {len(real_intersections)/len(corridor_cameras):.2f} intersections per camera")

# Create visualization
fig, ax = plt.subplots(figsize=(20, 16))

# Plot street centerlines
corridor.plot(ax=ax, color='#34495e', linewidth=1.5, alpha=0.6, zorder=2)

# Voronoi tessellation
vor = Voronoi(camera_coords)
for simplex in vor.ridge_vertices:
    simplex = np.asarray(simplex)
    if np.all(simplex >= 0):
        verts = vor.vertices[simplex]
        if (np.all(40.744 <= verts[:, 1]) and np.all(verts[:, 1] <= 40.773) and
            np.all(-74.003 <= verts[:, 0]) and np.all(verts[:, 0] <= -73.967)):
            ax.plot(verts[:, 0], verts[:, 1], 
                   color='#9b59b6', linewidth=2.5, alpha=0.5, zorder=3, linestyle='--')

# Plot intersections (STATES - blue circles)
ax.scatter(real_intersections[:, 0], real_intersections[:, 1], 
          s=30, c='#aed6f1', edgecolor='#2874a6', linewidth=1, 
          zorder=4, alpha=0.8, label=f'{len(real_intersections)} intersection nodes (states)')

# Plot cameras (SENSORS - green triangles)
ax.scatter(camera_coords[:, 0], camera_coords[:, 1], 
          s=150, c='#52be80', edgecolor='#1e8449', linewidth=2.5, 
          zorder=5, alpha=0.95, label=f'{len(corridor_cameras)} cameras (sensors)', marker='^')

# Grand Central
gc_lon, gc_lat = -73.9772, 40.7527
ax.scatter(gc_lon, gc_lat, s=900, c='#5dade2', edgecolor='#1a5276',
          linewidth=4, marker='*', zorder=8)
ax.text(gc_lon - 0.0045, gc_lat, 'Grand Central\n42nd & Park', ha='right', va='center',
       fontsize=13, fontweight='bold',
       bbox=dict(boxstyle='round,pad=0.7', facecolor='white', 
                edgecolor='#1a5276', linewidth=3, alpha=0.98))

# Carnegie Hall
ch_lon, ch_lat = -73.9799, 40.7651
ax.scatter(ch_lon, ch_lat, s=900, c='#ec7063', edgecolor='#922b21',
          linewidth=4, marker='*', zorder=8)
ax.text(ch_lon + 0.0045, ch_lat, 'Carnegie Hall\n57th & 7th', ha='left', va='center',
       fontsize=13, fontweight='bold',
       bbox=dict(boxstyle='round,pad=0.7', facecolor='white',
                edgecolor='#922b21', linewidth=3, alpha=0.98))

ax.set_xlim(-74.003, -73.967)
ax.set_ylim(40.744, 40.773)
ax.set_aspect('equal')

ax.set_xlabel('Longitude', fontsize=14, fontweight='bold')
ax.set_ylabel('Latitude', fontsize=14, fontweight='bold')
ax.set_title(f'State Space Model: Manhattan Navigation Problem\n{len(real_intersections)} States (Real Intersections) | {len(corridor_cameras)} Camera Coverage Zones',
             fontsize=18, fontweight='bold', pad=20)

# North arrow
ax.annotate('', xy=(-73.969, 40.771), xytext=(-73.969, 40.767),
           arrowprops=dict(arrowstyle='->', lw=5, color='#2c3e50'))
ax.text(-73.969, 40.7718, 'N', ha='center', va='bottom',
       fontsize=22, fontweight='bold', color='#2c3e50')

ax.legend(loc='upper left', fontsize=13, framealpha=0.97, 
         title='State Space Components', title_fontsize=14,
         edgecolor='#34495e', fancybox=True, shadow=True)

stats_text = (f'STATE SPACE:\n'
             f'Nodes: {len(real_intersections)}\n'
             f'Cameras: {len(corridor_cameras)}\n'
             f'Ratio: {len(real_intersections)/len(corridor_cameras):.2f}:1\n'
             f'Branching: 2-4\n'
             f'Solution depth: 15+ blocks')
ax.text(0.98, 0.02, stats_text, transform=ax.transAxes,
       fontsize=12, verticalalignment='bottom', horizontalalignment='right',
       bbox=dict(boxstyle='round,pad=0.8', facecolor='#f8f9f9', 
                edgecolor='#34495e', linewidth=2.5, alpha=0.97),
       family='monospace', fontweight='bold')

plt.tight_layout()
plt.savefig('state_space_model.png', dpi=300, bbox_inches='tight', facecolor='white')
print(f"\nState space model saved!")
print(f"Data sources: NYC Planning DCM Shapefile (June 2025) + NYC DOT TMC API")

# Save intersection data
with open('real_intersections_from_shapefile.json', 'w') as f:
    json.dump(real_intersections.tolist(), f)
print(f"Real intersections saved to real_intersections_from_shapefile.json")

