#!/usr/bin/env python3
"""Final state space map using full DCM and real intersection data"""

import matplotlib.pyplot as plt
import numpy as np
import json
from scipy.spatial import Voronoi

# Load full DCM (Digital City Map)
print("Loading full DCM...")
with open('manhattan_dcm_full.geojson', 'r') as f:
    dcm_data = json.load(f)

# Load real intersections
with open('real_intersections.json', 'r') as f:
    real_intersections = np.array(json.load(f))

# Load cameras
with open('nyc_cameras_full.json', 'r') as f:
    all_cameras = json.load(f)

# Filter cameras
corridor_cameras = []
for cam in all_cameras:
    try:
        lat = float(cam['latitude'])
        lon = float(cam['longitude'])
        area = cam.get('area', '')
        
        if (area == 'Manhattan' and 
            40.745 <= lat <= 40.772 and 
            -74.002 <= lon <= -73.968):
            corridor_cameras.append(cam)
    except:
        pass

camera_coords = np.array([[float(cam['longitude']), float(cam['latitude'])] 
                          for cam in corridor_cameras])

print(f"Real intersections: {len(real_intersections)}")
print(f"Cameras: {len(corridor_cameras)}")

# Create figure
fig, ax = plt.subplots(figsize=(18, 14))

# Plot DCM features (streets and infrastructure)
street_count = 0
for feature in dcm_data['features']:
    if feature['geometry']['type'] == 'LineString':
        coords = feature['geometry']['coordinates']
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        
        feat_type = feature['properties'].get('Feat_Type', '')
        
        # Only plot in corridor
        if (any(40.744 <= lat <= 40.773 for lat in lats) and
            any(-74.003 <= lon <= -73.967 for lon in lons)):
            
            if feat_type == 'Mapped_St':
                ax.plot(lons, lats, color='#34495e', linewidth=1.5, 
                       alpha=0.7, zorder=2, solid_capstyle='round')
                street_count += 1
            elif feat_type == 'Infrastructure':
                ax.plot(lons, lats, color='#95a5a6', linewidth=0.8, 
                       alpha=0.4, zorder=1, linestyle=':')

print(f"Plotted {street_count} street segments from DCM")

# Voronoi tessellation
vor = Voronoi(camera_coords)
for simplex in vor.ridge_vertices:
    simplex = np.asarray(simplex)
    if np.all(simplex >= 0):
        verts = vor.vertices[simplex]
        if (np.all(40.744 <= verts[:, 1]) and np.all(verts[:, 1] <= 40.773) and
            np.all(-74.003 <= verts[:, 0]) and np.all(verts[:, 0] <= -73.967)):
            ax.plot(verts[:, 0], verts[:, 1], 
                   color='#9b59b6', linewidth=2.5, alpha=0.6, zorder=3, linestyle='--')

# Plot REAL intersections (blue circles - STATES)
ax.scatter(real_intersections[:, 0], real_intersections[:, 1], 
          s=40, c='#aed6f1', edgecolor='#2874a6', linewidth=1.2, 
          zorder=4, alpha=0.9, label=f'{len(real_intersections)} intersection nodes (states)')

# Plot cameras (green triangles - SENSORS)
ax.scatter(camera_coords[:, 0], camera_coords[:, 1], 
          s=140, c='#52be80', edgecolor='#1e8449', linewidth=2.5, 
          zorder=5, alpha=0.95, label=f'{len(corridor_cameras)} cameras (sensors)', marker='^')

# Grand Central
gc_lon, gc_lat = -73.9772, 40.7527
ax.scatter(gc_lon, gc_lat, s=800, c='#5dade2', edgecolor='#1a5276',
          linewidth=4, marker='*', zorder=8)
ax.text(gc_lon - 0.004, gc_lat, 'Grand Central\n42nd & Park', ha='right', va='center',
       fontsize=12, fontweight='bold',
       bbox=dict(boxstyle='round,pad=0.7', facecolor='white', 
                edgecolor='#1a5276', linewidth=3, alpha=0.98))

# Carnegie Hall
ch_lon, ch_lat = -73.9799, 40.7651
ax.scatter(ch_lon, ch_lat, s=800, c='#ec7063', edgecolor='#922b21',
          linewidth=4, marker='*', zorder=8)
ax.text(ch_lon + 0.004, ch_lat, 'Carnegie Hall\n57th & 7th', ha='left', va='center',
       fontsize=12, fontweight='bold',
       bbox=dict(boxstyle='round,pad=0.7', facecolor='white',
                edgecolor='#922b21', linewidth=3, alpha=0.98))

ax.set_xlim(-74.003, -73.967)
ax.set_ylim(40.744, 40.773)
ax.set_aspect('equal')

ax.set_xlabel('Longitude', fontsize=14, fontweight='bold', color='#2c3e50')
ax.set_ylabel('Latitude', fontsize=14, fontweight='bold', color='#2c3e50')
ax.set_title('State Space Model: Manhattan Navigation (Grand Central to Carnegie Hall)\n' +
             f'{len(real_intersections)} States (Real Intersections) | {len(corridor_cameras)} Camera Coverage Zones (Voronoi Tessellation)',
             fontsize=17, fontweight='bold', pad=20, color='#2c3e50')

# North arrow
ax.annotate('', xy=(-73.969, 40.771), xytext=(-73.969, 40.767),
           arrowprops=dict(arrowstyle='->', lw=5, color='#2c3e50'))
ax.text(-73.969, 40.7718, 'N', ha='center', va='bottom',
       fontsize=22, fontweight='bold', color='#2c3e50')

ax.legend(loc='upper left', fontsize=12, framealpha=0.97, 
         title='State Space Components', title_fontsize=14,
         edgecolor='#34495e', fancybox=True, shadow=True)

stats_text = (f'STATE SPACE:\n'
             f'Nodes: {len(real_intersections)}\n'
             f'Camera zones: {len(corridor_cameras)}\n'
             f'Ratio: {len(real_intersections)/len(corridor_cameras):.2f}:1\n'
             f'Branching: 2-4\n'
             f'Min depth: 15 blocks')
ax.text(0.98, 0.02, stats_text, transform=ax.transAxes,
       fontsize=11, verticalalignment='bottom', horizontalalignment='right',
       bbox=dict(boxstyle='round,pad=0.8', facecolor='#f8f9f9', 
                edgecolor='#34495e', linewidth=2.5, alpha=0.97),
       family='monospace', color='#2c3e50', fontweight='bold')

ax.grid(True, alpha=0.15, linewidth=0.6, color='#7f8c8d', linestyle=':')

plt.tight_layout()
plt.savefig('state_space_model.png', dpi=300, bbox_inches='tight', facecolor='white')
print(f"\nFinal state space model saved to state_space_model.png")
print(f"Using official NYC Planning DCM data for streets")

