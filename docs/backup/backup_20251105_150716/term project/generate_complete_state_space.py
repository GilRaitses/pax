#!/usr/bin/env python3
"""Complete state space model with grid, intersections, and cameras"""

import matplotlib.pyplot as plt
import numpy as np
import json
from scipy.spatial import Voronoi

# Load camera data
with open('nyc_cameras_full.json', 'r') as f:
    all_cameras = json.load(f)

# Filter cameras for corridor
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

# Load street centerlines
with open('manhattan_streets.geojson', 'r') as f:
    streets_data = json.load(f)

# Create 140 intersection grid (20 streets × 7 avenues)
streets_lat = np.linspace(40.750, 40.770, 20)  # 40th to 59th (20 streets)
avenues_lon = np.linspace(-73.970, -74.000, 7)  # Lex to 8th (7 avenues)

intersections = []
for st_lat in streets_lat:
    for ave_lon in avenues_lon:
        intersections.append([ave_lon, st_lat])

intersections = np.array(intersections)

# Extract camera coordinates
camera_coords = np.array([[float(cam['longitude']), float(cam['latitude'])] 
                          for cam in corridor_cameras])

print(f"Intersections: {len(intersections)}")
print(f"Cameras: {len(corridor_cameras)}")
print(f"Ratio: {len(intersections)/len(corridor_cameras):.2f} intersections per camera")

# Create figure
fig, ax = plt.subplots(figsize=(18, 14))

# Plot official street centerlines (gray background)
street_count = 0
for feature in streets_data['features']:
    if feature['geometry']['type'] == 'LineString':
        coords = feature['geometry']['coordinates']
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        
        # Only plot streets in corridor
        if (any(40.744 <= lat <= 40.773 for lat in lats) and
            any(-74.003 <= lon <= -73.967 for lon in lons)):
            ax.plot(lons, lats, color='#d5d8dc', linewidth=1.2, 
                   alpha=0.6, zorder=1)
            street_count += 1

print(f"Plotted {street_count} street segments")

# Draw grid lines for streets and avenues
for st_lat in streets_lat:
    ax.axhline(st_lat, color='#ecf0f1', linewidth=0.8, alpha=0.7, zorder=2)

for ave_lon in avenues_lon:
    ax.axvline(ave_lon, color='#ecf0f1', linewidth=0.8, alpha=0.7, zorder=2)

# Compute Voronoi tessellation from camera positions
vor = Voronoi(camera_coords)
for simplex in vor.ridge_vertices:
    simplex = np.asarray(simplex)
    if np.all(simplex >= 0):
        # Clip to visible area
        verts = vor.vertices[simplex]
        if (np.all(40.744 <= verts[:, 1]) and np.all(verts[:, 1] <= 40.773) and
            np.all(-74.003 <= verts[:, 0]) and np.all(verts[:, 0] <= -73.967)):
            ax.plot(verts[:, 0], verts[:, 1], 
                   color='#9b59b6', linewidth=2, alpha=0.6, zorder=3, linestyle='--')

# Plot intersection nodes (BLUE circles - these are the states!)
ax.scatter(intersections[:, 0], intersections[:, 1], 
          s=35, c='#aed6f1', edgecolor='#2874a6', linewidth=1, 
          zorder=4, alpha=0.9, label=f'{len(intersections)} intersection nodes (states)')

# Plot cameras (GREEN triangles - sensors!)
ax.scatter(camera_coords[:, 0], camera_coords[:, 1], 
          s=120, c='#52be80', edgecolor='#1e8449', linewidth=2, 
          zorder=5, alpha=0.95, label=f'{len(corridor_cameras)} cameras (sensors)', marker='^')

# Mark Grand Central (START)
gc_lon, gc_lat = -73.9772, 40.7527
ax.scatter(gc_lon, gc_lat, s=700, c='#5dade2', edgecolor='#1a5276',
          linewidth=4, marker='*', zorder=8, label='START: Grand Central')
ax.text(gc_lon - 0.003, gc_lat, 'Grand Central\n42nd & Park', ha='right', va='center',
       fontsize=11, fontweight='bold',
       bbox=dict(boxstyle='round,pad=0.6', facecolor='white', 
                edgecolor='#1a5276', linewidth=2.5, alpha=0.98))

# Mark Carnegie Hall (GOAL)
ch_lon, ch_lat = -73.9799, 40.7651
ax.scatter(ch_lon, ch_lat, s=700, c='#ec7063', edgecolor='#922b21',
          linewidth=4, marker='*', zorder=8, label='GOAL: Carnegie Hall')
ax.text(ch_lon + 0.003, ch_lat, 'Carnegie Hall\n57th & 7th', ha='left', va='center',
       fontsize=11, fontweight='bold',
       bbox=dict(boxstyle='round,pad=0.6', facecolor='white',
                edgecolor='#922b21', linewidth=2.5, alpha=0.98))

# Set bounds
ax.set_xlim(-74.003, -73.967)
ax.set_ylim(40.744, 40.773)
ax.set_aspect('equal')

# Labels
ax.set_xlabel('Longitude', fontsize=13, fontweight='bold', color='#2c3e50')
ax.set_ylabel('Latitude', fontsize=13, fontweight='bold', color='#2c3e50')
ax.set_title('State Space Model: Manhattan Navigation Problem\n' +
             f'{len(intersections)} States (Intersections) | {len(corridor_cameras)} Camera Coverage Zones',
             fontsize=17, fontweight='bold', pad=20, color='#2c3e50')

# North arrow
ax.annotate('', xy=(-73.969, 40.771), xytext=(-73.969, 40.767),
           arrowprops=dict(arrowstyle='->', lw=4, color='#2c3e50'))
ax.text(-73.969, 40.7717, 'N', ha='center', va='bottom',
       fontsize=20, fontweight='bold', color='#2c3e50')

# Legend
ax.legend(loc='upper left', fontsize=11, framealpha=0.97, 
         title='State Space Components', title_fontsize=13,
         edgecolor='#34495e', fancybox=True, shadow=True)

# Stats box
stats_text = (f'STATE SPACE STATISTICS:\n'
             f'Intersection nodes: {len(intersections)}\n'
             f'Camera zones: {len(corridor_cameras)}\n'
             f'Coverage ratio: {len(corridor_cameras)/len(intersections):.2f}x\n'
             f'Branching factor: 2-4\n'
             f'Min solution depth: 15 blocks\n\n'
             f'Data sources:\n'
             f'• NYC Planning DCM\n'
             f'• NYC DOT TMC API')
ax.text(0.98, 0.02, stats_text, transform=ax.transAxes,
       fontsize=10, verticalalignment='bottom', horizontalalignment='right',
       bbox=dict(boxstyle='round,pad=0.8', facecolor='#f8f9f9', 
                edgecolor='#34495e', linewidth=2, alpha=0.97),
       family='monospace', color='#2c3e50')

ax.grid(True, alpha=0.15, linewidth=0.5, color='#7f8c8d')

plt.tight_layout()
plt.savefig('state_space_model.png', dpi=300, bbox_inches='tight', facecolor='white')
print(f"\nComplete state space model saved!")
print(f"\nKey insight: Voronoi tessellation assigns each intersection")
print(f"to its nearest camera, creating camera coverage zones.")

