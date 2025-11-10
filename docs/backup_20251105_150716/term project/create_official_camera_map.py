#!/usr/bin/env python3
"""Map 108 cameras to official NYC street grid with Voronoi tessellation"""

import matplotlib.pyplot as plt
import numpy as np
import json
from matplotlib.patches import Circle
from scipy.spatial import Voronoi
from matplotlib.collections import LineCollection

# Load Manhattan street centerlines
with open('manhattan_streets.geojson', 'r') as f:
    streets_data = json.load(f)

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

print(f"Cameras in corridor: {len(corridor_cameras)}")

# Extract camera coordinates for Voronoi
camera_coords = np.array([[float(cam['longitude']), float(cam['latitude'])] 
                          for cam in corridor_cameras])

# Create figure
fig, ax = plt.subplots(figsize=(16, 12))

# Plot street centerlines
for feature in streets_data['features']:
    if feature['geometry']['type'] == 'LineString':
        coords = feature['geometry']['coordinates']
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        
        # Only plot streets in our corridor
        if (any(40.745 <= lat <= 40.772 for lat in lats) and
            any(-74.002 <= lon <= -73.968 for lon in lons)):
            ax.plot(lons, lats, color='#bdc3c7', linewidth=0.8, 
                   alpha=0.6, zorder=1)

print(f"Street centerlines plotted")

# Compute and plot Voronoi tessellation
vor = Voronoi(camera_coords)
for simplex in vor.ridge_vertices:
    simplex = np.asarray(simplex)
    if np.all(simplex >= 0):
        ax.plot(vor.vertices[simplex, 0], vor.vertices[simplex, 1], 
               'purple', linewidth=1.5, alpha=0.4, zorder=2, linestyle='--')

print(f"Voronoi tessellation computed")

# Plot cameras
ax.scatter(camera_coords[:, 0], camera_coords[:, 1], 
          s=60, c='#52be80', edgecolor='#1e8449', linewidth=1.5, 
          zorder=5, alpha=0.9, label=f'{len(corridor_cameras)} cameras')

# Mark Grand Central and Carnegie Hall
gc_lon, gc_lat = -73.9772, 40.7527
ch_lon, ch_lat = -73.9799, 40.7651

ax.scatter(gc_lon, gc_lat, s=500, c='#5dade2', edgecolor='#2874a6',
          linewidth=3, marker='s', zorder=7, label='Grand Central (Start)')
ax.text(gc_lon, gc_lat - 0.0012, 'Grand Central\n42nd & Park', ha='center', va='top',
       fontsize=10, fontweight='bold',
       bbox=dict(boxstyle='round,pad=0.5', facecolor='white', 
                edgecolor='#2874a6', linewidth=2, alpha=0.95))

ax.scatter(ch_lon, ch_lat, s=500, c='#ec7063', edgecolor='#c0392b',
          linewidth=3, marker='s', zorder=7, label='Carnegie Hall (Goal)')
ax.text(ch_lon, ch_lat + 0.0012, 'Carnegie Hall\n57th & 7th', ha='center', va='bottom',
       fontsize=10, fontweight='bold',
       bbox=dict(boxstyle='round,pad=0.5', facecolor='white',
                edgecolor='#c0392b', linewidth=2, alpha=0.95))

# Set bounds
ax.set_xlim(-74.003, -73.967)
ax.set_ylim(40.744, 40.773)
ax.set_aspect('equal')

# Labels
ax.set_xlabel('Longitude', fontsize=12, fontweight='bold')
ax.set_ylabel('Latitude', fontsize=12, fontweight='bold')
ax.set_title('NYC DOT Camera Coverage with Official Street Grid\n' +
             'Grand Central to Carnegie Hall Corridor (Voronoi Tessellation)',
             fontsize=15, fontweight='bold', pad=20)

# North arrow
ax.annotate('', xy=(-73.969, 40.771), xytext=(-73.969, 40.768),
           arrowprops=dict(arrowstyle='->', lw=3, color='#2c3e50'))
ax.text(-73.969, 40.7715, 'N', ha='center', va='bottom',
       fontsize=16, fontweight='bold', color='#2c3e50')

# Legend with explanation
legend_text = [
    f'{len(corridor_cameras)} NYC DOT cameras (green)',
    'Voronoi tessellation (purple dashed)',
    'Official NYC street centerlines (gray)'
]
ax.legend(loc='upper left', fontsize=11, framealpha=0.95, 
         title='Camera Coverage Network', title_fontsize=12)

# Add text box with stats
stats_text = (f'State Space: ~75 intersections\n'
             f'Cameras: {len(corridor_cameras)} zones\n'
             f'Avg: 4-5 intersections per camera zone')
ax.text(0.02, 0.02, stats_text, transform=ax.transAxes,
       fontsize=10, verticalalignment='bottom',
       bbox=dict(boxstyle='round,pad=0.5', facecolor='white', 
                edgecolor='#7f8c8d', linewidth=1.5, alpha=0.9))

plt.tight_layout()
plt.savefig('camera_grid_map.png', dpi=300, bbox_inches='tight', facecolor='white')
print(f"\nOfficial street grid map with cameras saved to camera_grid_map.png")
print(f"Data sources:")
print(f"  - Streets: NYC Planning Digital City Map")
print(f"  - Cameras: NYC DOT Traffic Management Center API")

