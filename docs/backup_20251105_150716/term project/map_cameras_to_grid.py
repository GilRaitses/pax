#!/usr/bin/env python3
"""Map the 108 cameras to Manhattan street grid"""

import matplotlib.pyplot as plt
import numpy as np
import json
from matplotlib.patches import Circle
from scipy.spatial import Voronoi, voronoi_plot_2d

# Load camera data
with open('nyc_cameras_full.json', 'r') as f:
    all_cameras = json.load(f)

# Filter for the corridor
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

print(f"Found {len(corridor_cameras)} cameras in corridor")

# Extract coordinates
camera_coords = np.array([[float(cam['longitude']), float(cam['latitude'])] 
                          for cam in corridor_cameras])

# Create figure
fig, ax = plt.subplots(figsize=(14, 10))

# Plot cameras
ax.scatter(camera_coords[:, 0], camera_coords[:, 1], 
          s=80, c='#52be80', edgecolor='#1e8449', linewidth=2, 
          zorder=5, alpha=0.8, label=f'Cameras (n={len(corridor_cameras)})')

# Mark Grand Central and Carnegie Hall
gc_lon, gc_lat = -73.9772, 40.7527
ch_lon, ch_lat = -73.9799, 40.7651

ax.scatter(gc_lon, gc_lat, s=400, c='#5dade2', edgecolor='#2874a6',
          linewidth=3, marker='s', zorder=6, label='Grand Central (Start)')
ax.text(gc_lon, gc_lat - 0.0008, 'GC', ha='center', va='top',
       fontsize=12, fontweight='bold',
       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9))

ax.scatter(ch_lon, ch_lat, s=400, c='#ec7063', edgecolor='#c0392b',
          linewidth=3, marker='s', zorder=6, label='Carnegie Hall (Goal)')
ax.text(ch_lon, ch_lat + 0.0008, 'CH', ha='center', va='bottom',
       fontsize=12, fontweight='bold',
       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9))

# Draw grid lines for major streets
streets = {
    '40th': 40.750,
    '42nd': 40.7527,
    '45th': 40.756,
    '48th': 40.760,
    '51st': 40.763,
    '54th': 40.766,
    '57th': 40.7651,
    '59th': 40.770
}

for street, lat in streets.items():
    ax.axhline(lat, color='#d5d8dc', linewidth=0.8, alpha=0.6, zorder=1)
    ax.text(-74.003, lat, street, fontsize=8, ha='right', va='center', color='#7f8c8d')

# Approximate avenue positions
avenues = {
    'Lex': -73.970,
    'Park': -73.973,
    'Madison': -73.976,
    '5th': -73.980,
    '6th': -73.985,
    'Broad': -73.987,
    '7th': -73.990,
    '8th': -73.995
}

for ave, lon in avenues.items():
    ax.axvline(lon, color='#d5d8dc', linewidth=0.8, alpha=0.6, zorder=1)
    ax.text(lon, 40.744, ave, fontsize=8, ha='center', va='top', 
           color='#7f8c8d', rotation=45)

# Compute Voronoi tessellation
try:
    vor = Voronoi(camera_coords)
    # Plot Voronoi edges
    for simplex in vor.ridge_vertices:
        simplex = np.asarray(simplex)
        if np.all(simplex >= 0):
            ax.plot(vor.vertices[simplex, 0], vor.vertices[simplex, 1], 
                   'k-', linewidth=0.5, alpha=0.3, zorder=2)
    print("Voronoi tessellation computed successfully")
except Exception as e:
    print(f"Voronoi computation: {e}")

# Set bounds
ax.set_xlim(-74.003, -73.967)
ax.set_ylim(40.744, 40.773)
ax.set_aspect('equal')

# Labels
ax.set_xlabel('Longitude', fontsize=11, fontweight='bold')
ax.set_ylabel('Latitude', fontsize=11, fontweight='bold')
ax.set_title('NYC DOT Camera Coverage: Grand Central to Carnegie Hall\n' +
             f'{len(corridor_cameras)} cameras with Voronoi tessellation',
             fontsize=14, fontweight='bold', pad=15)

# Add north arrow
ax.annotate('', xy=(-73.969, 40.771), xytext=(-73.969, 40.768),
           arrowprops=dict(arrowstyle='->', lw=3, color='#2c3e50'))
ax.text(-73.969, 40.7715, 'N', ha='center', va='bottom',
       fontsize=14, fontweight='bold', color='#2c3e50')

ax.legend(loc='upper left', fontsize=10, framealpha=0.95)
ax.grid(True, alpha=0.2)

plt.tight_layout()
plt.savefig('camera_grid_map.png', dpi=300, bbox_inches='tight', facecolor='white')
print(f"\nCamera grid map saved to camera_grid_map.png")
print(f"Camera density: {len(corridor_cameras)/((40.772-40.745)*(74.002-73.968)):.1f} cameras per sq degree")


