#!/usr/bin/env python3
"""Generate final state space visualization from NYC Planning shapefile"""

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import json
from scipy.spatial import Voronoi

# Load corridor data
print("Loading corridor streets...")
dcm = gpd.read_file('DCM_StreetCenterLine.shp')
dcm_latlon = dcm.to_crs(epsg=4326)
manhattan = dcm_latlon[dcm_latlon['Borough'] == 'Manhattan'].copy()

# Filter corridor
corridor_streets = []
for idx, row in manhattan.iterrows():
    bounds = row.geometry.bounds
    if not (bounds[2] < -74.002 or bounds[0] > -73.968 or
            bounds[3] < 40.745 or bounds[1] > 40.772):
        corridor_streets.append(row)

corridor = gpd.GeoDataFrame(corridor_streets, crs='EPSG:4326')

# Extract intersections
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

intersections = np.array(list(intersection_coords))

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

print(f"Intersections: {len(intersections)}")
print(f"Cameras: {len(corridor_cameras)}")

# Create figure
fig, ax = plt.subplots(figsize=(20, 16))

# Plot streets
corridor.plot(ax=ax, color='#34495e', linewidth=1.5, alpha=0.65, zorder=2)

# Voronoi
vor = Voronoi(camera_coords)
for simplex in vor.ridge_vertices:
    simplex = np.asarray(simplex)
    if np.all(simplex >= 0):
        verts = vor.vertices[simplex]
        if (np.all(40.744 <= verts[:, 1]) and np.all(verts[:, 1] <= 40.773) and
            np.all(-74.003 <= verts[:, 0]) and np.all(verts[:, 0] <= -73.967)):
            ax.plot(verts[:, 0], verts[:, 1], 
                   color='#9b59b6', linewidth=2.5, alpha=0.5, zorder=3, linestyle='--')

# Intersections (STATES)
ax.scatter(intersections[:, 0], intersections[:, 1], 
          s=25, c='#aed6f1', edgecolor='#2874a6', linewidth=0.8, 
          zorder=4, alpha=0.85, label=f'{len(intersections)} intersection nodes (states)')

# Cameras (SENSORS)
ax.scatter(camera_coords[:, 0], camera_coords[:, 1], 
          s=150, c='#52be80', edgecolor='#1e8449', linewidth=2.5, 
          zorder=5, alpha=0.95, label=f'{len(corridor_cameras)} cameras (sensors)', marker='^')

# Start and Goal
gc_lon, gc_lat = -73.9772, 40.7527
ch_lon, ch_lat = -73.9799, 40.7651

ax.scatter(gc_lon, gc_lat, s=1000, c='#5dade2', edgecolor='#1a5276',
          linewidth=4, marker='*', zorder=8)
ax.text(gc_lon - 0.005, gc_lat, 'Grand Central\n42nd & Park', ha='right', va='center',
       fontsize=13, fontweight='bold',
       bbox=dict(boxstyle='round,pad=0.7', facecolor='white', 
                edgecolor='#1a5276', linewidth=3, alpha=0.98))

ax.scatter(ch_lon, ch_lat, s=1000, c='#ec7063', edgecolor='#922b21',
          linewidth=4, marker='*', zorder=8)
ax.text(ch_lon + 0.005, ch_lat, 'Carnegie Hall\n57th & 7th', ha='left', va='center',
       fontsize=13, fontweight='bold',
       bbox=dict(boxstyle='round,pad=0.7', facecolor='white',
                edgecolor='#922b21', linewidth=3, alpha=0.98))

ax.set_xlim(-74.003, -73.967)
ax.set_ylim(40.744, 40.773)
ax.set_aspect('equal')

ax.set_xlabel('Longitude', fontsize=14, fontweight='bold')
ax.set_ylabel('Latitude', fontsize=14, fontweight='bold')
ax.set_title(f'State Space: Manhattan Navigation Problem\n{len(intersections)} Intersection Nodes | {len(corridor_cameras)} Camera Coverage Zones (Voronoi Tessellation)',
             fontsize=18, fontweight='bold', pad=20)

# North arrow
ax.annotate('', xy=(-73.969, 40.771), xytext=(-73.969, 40.767),
           arrowprops=dict(arrowstyle='->', lw=5, color='#2c3e50'))
ax.text(-73.969, 40.7718, 'N', ha='center', va='bottom',
       fontsize=22, fontweight='bold', color='#2c3e50')

ax.legend(loc='upper left', fontsize=13, framealpha=0.97, 
         title='Components', title_fontsize=14,
         edgecolor='#34495e', fancybox=True, shadow=True)

stats = (f'STATE SPACE:\n'
        f'Nodes: {len(intersections)}\n'
        f'Cameras: {len(corridor_cameras)}\n'
        f'Ratio: {len(intersections)/len(corridor_cameras):.1f}:1\n'
        f'Branching: 2-4\n'
        f'Min depth: 15 blocks')
ax.text(0.98, 0.02, stats, transform=ax.transAxes,
       fontsize=12, va='bottom', ha='right',
       bbox=dict(boxstyle='round,pad=0.8', facecolor='#f8f9f9', 
                edgecolor='#34495e', linewidth=2.5, alpha=0.97),
       family='monospace', fontweight='bold')

ax.grid(True, alpha=0.12, linewidth=0.5, color='#7f8c8d', linestyle=':')

plt.tight_layout()
plt.savefig('state_space_model.png', dpi=300, bbox_inches='tight', facecolor='white')
print(f"\nState space model saved to state_space_model.png")

