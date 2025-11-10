#!/usr/bin/env python3
"""Generate state space model: 140 intersections, 108 cameras, Voronoi tessellation"""

import matplotlib.pyplot as plt
import numpy as np
import json
from matplotlib.patches import Circle
from scipy.spatial import Voronoi

# Load camera data
with open('nyc_cameras_full.json', 'r') as f:
    all_cameras = json.load(f)

# Filter cameras for corridor (40th to 59th, Lex to 8th)
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

# Load Manhattan street centerlines
with open('manhattan_streets.geojson', 'r') as f:
    streets_data = json.load(f)

# Generate 140 intersection grid (20 streets × 7 avenues)
streets = np.linspace(40.750, 40.770, 20)  # 40th to 59th St
avenues = np.linspace(-73.970, -74.000, 7)  # Lex to 8th Ave

# Create intersection nodes
intersections = []
for st in streets:
    for ave in avenues:
        intersections.append([ave, st])

intersections = np.array(intersections)
print(f"Intersections: {len(intersections)}")

# Extract camera coordinates
camera_coords = np.array([[float(cam['longitude']), float(cam['latitude'])] 
                          for cam in corridor_cameras])

# Create figure
fig, ax = plt.subplots(figsize=(16, 14))

# Plot street centerlines from official NYC data
for feature in streets_data['features']:
    if feature['geometry']['type'] == 'LineString':
        coords = feature['geometry']['coordinates']
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        
        # Only plot streets in corridor
        if (any(40.744 <= lat <= 40.773 for lat in lats) and
            any(-74.003 <= lon <= -73.967 for lon in lons)):
            ax.plot(lons, lats, color='#bdc3c7', linewidth=1, 
                   alpha=0.5, zorder=1)

# Compute Voronoi tessellation from camera positions
vor = Voronoi(camera_coords)
for simplex in vor.ridge_vertices:
    simplex = np.asarray(simplex)
    if np.all(simplex >= 0):
        ax.plot(vor.vertices[simplex, 0], vor.vertices[simplex, 1], 
               color='#9b59b6', linewidth=2, alpha=0.5, zorder=3, linestyle='--')

# Plot intersection nodes (smaller, gray)
ax.scatter(intersections[:, 0], intersections[:, 1], 
          s=15, c='#ecf0f1', edgecolor='#95a5a6', linewidth=0.5, 
          zorder=4, alpha=0.8, label=f'{len(intersections)} intersections')

# Plot cameras (larger, green)
ax.scatter(camera_coords[:, 0], camera_coords[:, 1], 
          s=100, c='#52be80', edgecolor='#1e8449', linewidth=2, 
          zorder=5, alpha=0.9, label=f'{len(corridor_cameras)} cameras', marker='^')

# Mark Grand Central and Carnegie Hall
gc_lon, gc_lat = -73.9772, 40.7527
ch_lon, ch_lat = -73.9799, 40.7651

ax.scatter(gc_lon, gc_lat, s=600, c='#5dade2', edgecolor='#2874a6',
          linewidth=3, marker='s', zorder=8, label='Start: Grand Central')
ax.text(gc_lon, gc_lat, 'GC', ha='center', va='center',
       fontsize=14, fontweight='bold', color='white', zorder=9)

ax.scatter(ch_lon, ch_lat, s=600, c='#ec7063', edgecolor='#c0392b',
          linewidth=3, marker='s', zorder=8, label='Goal: Carnegie Hall')
ax.text(ch_lon, ch_lat, 'CH', ha='center', va='center',
       fontsize=14, fontweight='bold', color='white', zorder=9)

# Sample route path (baseline: west then north)
route_lon = [gc_lon, -73.985, -73.990, -73.995, ch_lon, ch_lon]
route_lat = [gc_lat, gc_lat, gc_lat, gc_lat, gc_lat, ch_lat]
ax.plot(route_lon, route_lat, color='#3498db', linewidth=4, 
       linestyle='--', alpha=0.7, zorder=6, label='Example route')

# Set bounds
ax.set_xlim(-74.003, -73.967)
ax.set_ylim(40.744, 40.773)
ax.set_aspect('equal')

# Labels
ax.set_xlabel('Longitude', fontsize=13, fontweight='bold')
ax.set_ylabel('Latitude', fontsize=13, fontweight='bold')
ax.set_title('State Space Model: Grand Central to Carnegie Hall Navigation\n' +
             f'{len(intersections)} Intersection Nodes | {len(corridor_cameras)} Camera Coverage Zones (Voronoi Tessellation)',
             fontsize=16, fontweight='bold', pad=20)

# North arrow
ax.annotate('', xy=(-73.969, 40.771), xytext=(-73.969, 40.768),
           arrowprops=dict(arrowstyle='->', lw=4, color='#2c3e50'))
ax.text(-73.969, 40.7715, 'N', ha='center', va='bottom',
       fontsize=18, fontweight='bold', color='#2c3e50')

# Legend
ax.legend(loc='upper left', fontsize=11, framealpha=0.95, 
         title='State Space Components', title_fontsize=12)

# Stats box
stats_text = (f'State Space Statistics:\n'
             f'• Intersection nodes: {len(intersections)}\n'
             f'• Camera zones: {len(corridor_cameras)}\n'
             f'• Coverage: {len(corridor_cameras)/len(intersections)*100:.1f}%\n'
             f'• Avg branching factor: 2-4\n'
             f'• Min solution depth: 15 blocks')
ax.text(0.98, 0.02, stats_text, transform=ax.transAxes,
       fontsize=10, verticalalignment='bottom', horizontalalignment='right',
       bbox=dict(boxstyle='round,pad=0.7', facecolor='white', 
                edgecolor='#34495e', linewidth=2, alpha=0.95),
       family='monospace')

plt.tight_layout()
plt.savefig('state_space_model.png', dpi=300, bbox_inches='tight', facecolor='white')
print(f"\nState space model saved to state_space_model.png")
print(f"\nModel details:")
print(f"  States (intersections): {len(intersections)}")
print(f"  Camera coverage zones: {len(corridor_cameras)}")
print(f"  Coverage ratio: {len(corridor_cameras)/len(intersections):.2f}")
print(f"  Data sources: NYC Planning DCM + NYC DOT TMC API")

