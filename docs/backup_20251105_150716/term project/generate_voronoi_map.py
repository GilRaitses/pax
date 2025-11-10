#!/usr/bin/env python3
"""Generate Voronoi tessellation map with street names"""

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import json
from scipy.spatial import Voronoi

# Load data
with open('actual_intersections.json', 'r') as f:
    data = json.load(f)
    intersections = np.array(data['coordinates'])

with open('nyc_cameras_full.json', 'r') as f:
    all_cameras = json.load(f)

corridor_cameras = []
for cam in all_cameras:
    try:
        lat, lon = float(cam['latitude']), float(cam['longitude'])
        if (cam.get('area') == 'Manhattan' and 
            40.745 <= lat <= 40.772 and -74.002 <= lon <= -73.968):
            corridor_cameras.append(cam)
    except:
        pass

camera_coords = np.array([[float(cam['longitude']), float(cam['latitude'])] 
                          for cam in corridor_cameras])

# Load streets
corridor_gdf = gpd.read_file('DCM_StreetCenterLine.shp').to_crs(epsg=4326)
manhattan = corridor_gdf[corridor_gdf['Borough'] == 'Manhattan']
corridor_streets = []
for idx, row in manhattan.iterrows():
    bounds = row.geometry.bounds
    if not (bounds[2] < -74.002 or bounds[0] > -73.968 or
            bounds[3] < 40.745 or bounds[1] > 40.772):
        corridor_streets.append(row)
corridor_gdf = gpd.GeoDataFrame(corridor_streets, crs='EPSG:4326')

# Create figure
fig, ax = plt.subplots(figsize=(18, 14))

# Plot streets (gray)
corridor_gdf.plot(ax=ax, color='#7f8c8d', linewidth=1.2, alpha=0.5, zorder=1)

# Plot Voronoi tessellation (purple dashed)
vor = Voronoi(camera_coords)
for simplex in vor.ridge_vertices:
    simplex = np.asarray(simplex)
    if np.all(simplex >= 0):
        verts = vor.vertices[simplex]
        if (np.all(40.744 <= verts[:, 1]) and np.all(verts[:, 1] <= 40.773) and
            np.all(-74.003 <= verts[:, 0]) and np.all(verts[:, 0] <= -73.967)):
            ax.plot(verts[:, 0], verts[:, 1], 
                   color='#9b59b6', linewidth=3, alpha=0.7, zorder=3, linestyle='--')

# Plot intersections (blue)
ax.scatter(intersections[:, 0], intersections[:, 1], 
          s=40, c='#aed6f1', edgecolor='#2874a6', linewidth=1.2, 
          zorder=4, alpha=0.85)

# Plot cameras (green triangles)
for i, cam in enumerate(corridor_cameras):
    lon, lat = float(cam['longitude']), float(cam['latitude'])
    ax.scatter(lon, lat, s=180, c='#52be80', edgecolor='#1e8449', 
              linewidth=2.5, zorder=5, alpha=0.95, marker='^')
    
    # Label a few cameras with street names
    if i % 15 == 0:  # Label every 15th camera
        name = cam['name'].replace(' @', '\n')
        ax.text(lon, lat + 0.0008, name, ha='center', va='bottom',
               fontsize=7, color='#1e8449', fontweight='bold',
               bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7))

# Mark start and goal
gc_lon, gc_lat = -73.9772, 40.7527
ch_lon, ch_lat = -73.9799, 40.7651

ax.scatter(gc_lon, gc_lat, s=1200, c='#5dade2', edgecolor='#1a5276',
          linewidth=4, marker='*', zorder=8)
ax.text(gc_lon - 0.006, gc_lat, 'GRAND CENTRAL\n42nd & Park', ha='right', va='center',
       fontsize=12, fontweight='bold',
       bbox=dict(boxstyle='round,pad=0.7', facecolor='white', 
                edgecolor='#1a5276', linewidth=3, alpha=0.98))

ax.scatter(ch_lon, ch_lat, s=1200, c='#ec7063', edgecolor='#922b21',
          linewidth=4, marker='*', zorder=8)
ax.text(ch_lon + 0.006, ch_lat, 'CARNEGIE HALL\n57th & 7th', ha='left', va='center',
       fontsize=12, fontweight='bold',
       bbox=dict(boxstyle='round,pad=0.7', facecolor='white',
                edgecolor='#922b21', linewidth=3, alpha=0.98))

ax.set_xlim(-74.003, -73.967)
ax.set_ylim(40.744, 40.773)
ax.set_aspect('equal')

ax.set_xlabel('Longitude', fontsize=14, fontweight='bold')
ax.set_ylabel('Latitude', fontsize=14, fontweight='bold')
ax.set_title('Voronoi Tessellation: Camera Coverage Zones\n' +
             f'{len(intersections)} Intersections | {len(corridor_cameras)} Camera Zones',
             fontsize=17, fontweight='bold', pad=20)

# North arrow
ax.annotate('', xy=(-73.969, 40.771), xytext=(-73.969, 40.767),
           arrowprops=dict(arrowstyle='->', lw=5, color='#2c3e50'))
ax.text(-73.969, 40.7718, 'N', ha='center', va='bottom',
       fontsize=22, fontweight='bold', color='#2c3e50')

# Legend
legend_elements = [
    plt.Line2D([0], [0], color='#9b59b6', linewidth=3, linestyle='--', label='Voronoi boundaries'),
    plt.scatter([], [], s=40, c='#aed6f1', edgecolor='#2874a6', label=f'{len(intersections)} intersections'),
    plt.scatter([], [], s=180, c='#52be80', edgecolor='#1e8449', marker='^', label=f'{len(corridor_cameras)} cameras'),
    plt.Line2D([0], [0], color='#7f8c8d', linewidth=1.2, alpha=0.5, label='Street centerlines')
]
ax.legend(handles=legend_elements, loc='upper left', fontsize=12, framealpha=0.97,
         title='Legend', title_fontsize=13, edgecolor='#34495e', fancybox=True)

ax.grid(True, alpha=0.12, linewidth=0.5, color='#95a5a6', linestyle=':')

plt.tight_layout()
plt.savefig('voronoi_tessellation.png', dpi=300, bbox_inches='tight', facecolor='white')
print(f"Voronoi tessellation map saved!")
print(f"Shows: {len(intersections)} intersections, {len(corridor_cameras)} cameras")
print(f"Voronoi cells assign each intersection to its nearest camera")

