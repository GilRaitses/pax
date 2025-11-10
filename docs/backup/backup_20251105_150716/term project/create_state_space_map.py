#!/usr/bin/env python3
"""Create actual state space map with Voronoi tessellation"""

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import json
import glob
from scipy.spatial import Voronoi
from shapely.geometry import box

# Load actual intersections with street names
with open('actual_intersections.json', 'r') as f:
    data = json.load(f)
    intersections = np.array(data['coordinates'])
    # Get intersection details if available
    if 'intersections' in data:
        intersection_details = data['intersections']
    else:
        intersection_details = {}

# Load cameras
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
streets = []
for idx, row in manhattan.iterrows():
    bounds = row.geometry.bounds
    if not (bounds[2] < -74.002 or bounds[0] > -73.968 or
            bounds[3] < 40.745 or bounds[1] > 40.772):
        streets.append(row)
corridor_gdf = gpd.GeoDataFrame(streets, crs='EPSG:4326')

print(f"Intersections: {len(intersections)}")
print(f"Cameras: {len(corridor_cameras)}")
print(f"Streets: {len(corridor_gdf)}")

# Load official parks shapefile (NYC OpenData export lives under NYC_Parks/)
parks_files = glob.glob('NYC_Parks/*.shp')
if not parks_files:
    raise FileNotFoundError("Park shapefile not found in NYC_Parks/. Download NYC Parks Properties shapefile to that folder.")
parks_gdf = gpd.read_file(parks_files[0]).to_crs(epsg=4326)

# Load official hydrography shapefile (NYC Planimetric Database - Hydrography)
water_files = glob.glob('NYC Planimetric Database_ Hydrography_20251102/*.shp')
if not water_files:
    raise FileNotFoundError("Hydrography shapefile not found in NYC Planimetric Database_ Hydrography_20251102/. Download NYC hydrography shapefile to that folder.")
water_gdf = gpd.read_file(water_files[0]).to_crs(epsg=4326)

# Clip to corridor bounding box for performance and accuracy
bbox_geom = box(-74.003, 40.744, -73.967, 40.773)
parks_clip = parks_gdf.clip(bbox_geom)
water_clip = water_gdf.clip(bbox_geom)

# Keep only Central Park polygons to avoid clutter from other parks
if 'signname' in parks_clip.columns:
    parks_clip = parks_clip[parks_clip['signname'].str.contains('Central Park', case=False, na=False)]
elif 'name' in parks_clip.columns:
    parks_clip = parks_clip[parks_clip['name'].str.contains('Central Park', case=False, na=False)]

print(f"Parks clipped: {len(parks_clip)}")
print(f"Water features clipped: {len(water_clip)}")

# Create figure
fig, ax = plt.subplots(figsize=(22, 18))

# Plot water (Hudson & East Rivers) using official polygons
if not water_clip.empty:
    water_clip.plot(ax=ax, facecolor='#3498db', edgecolor='#2980b9',
                    linewidth=0.6, alpha=0.4, zorder=0)

# Plot Central Park polygons (official footprint)
if not parks_clip.empty:
    parks_clip.plot(ax=ax, facecolor='#2ecc71', edgecolor='#27ae60',
                    linewidth=0.8, alpha=0.6, zorder=1)

# Plot street network (dark gray, thicker)
corridor_gdf.plot(ax=ax, color='#2c3e50', linewidth=1.8, alpha=0.7, zorder=2)

# Compute and plot Voronoi tessellation (solid soft yellow, semi-opaque)
vor = Voronoi(camera_coords)
for simplex in vor.ridge_vertices:
    simplex = np.asarray(simplex)
    if np.all(simplex >= 0):
        verts = vor.vertices[simplex]
        if (np.all(40.744 <= verts[:, 1]) and np.all(verts[:, 1] <= 40.773) and
            np.all(-74.003 <= verts[:, 0]) and np.all(verts[:, 0] <= -73.967)):
            # Create soft blurry effect with multiple very transparent layers
            for width, alpha in [(12, 0.05), (10, 0.08), (8, 0.1), (6, 0.12), (4, 0.15), (2, 0.18)]:
                ax.plot(verts[:, 0], verts[:, 1], 
                       color='#ffd700', linewidth=width, alpha=alpha, zorder=3, 
                       linestyle='-', solid_capstyle='round')

# Plot intersection nodes (WHITE circles with RED borders)
ax.scatter(intersections[:, 0], intersections[:, 1], 
          s=60, c='white', edgecolor='#c0392b', linewidth=2.5, 
          zorder=5, alpha=0.95, label=f'{len(intersections)} intersection nodes')

# Plot cameras (GREEN triangles, larger)
ax.scatter(camera_coords[:, 0], camera_coords[:, 1], 
          s=220, c='#27ae60', edgecolor='#196f3d', linewidth=3, 
          zorder=6, alpha=0.95, label=f'{len(corridor_cameras)} cameras', marker='^')

# Label key intersections with IDs
# Sample a few intersections to show node ID encoding
sample_indices = [0, 20, 40, 60, 80, 100, 120, 140]
for idx in sample_indices:
    if idx < len(intersections):
        lon, lat = intersections[idx]
        # Node ID: sequential number
        ax.text(lon, lat, f'n{idx}', ha='center', va='center',
               fontsize=7, color='#c0392b', fontweight='bold', zorder=7)

# Mark start and goal with special IDs
gc_lon, gc_lat = -73.9772, 40.7527
ch_lon, ch_lat = -73.9799, 40.7651

# START (Grand Central) - southeast, label positioned closer, diagonally below-right
ax.scatter(gc_lon, gc_lat, s=1400, c='#3498db', edgecolor='#1a5276',
          linewidth=5, marker='*', zorder=9)
# Use annotation with arrow for better connection
ax.annotate('START (s₀)\nGrand Central\n42nd & Park', 
           xy=(gc_lon, gc_lat), xytext=(gc_lon + 0.0015, gc_lat - 0.002),
           ha='left', va='top',
           fontsize=12, fontweight='bold',
           bbox=dict(boxstyle='round,pad=0.6', facecolor='white', 
                    edgecolor='#1a5276', linewidth=2.5, alpha=0.98),
           arrowprops=dict(arrowstyle='->', lw=2, color='#1a5276', 
                          connectionstyle='arc3,rad=0.1'),
           zorder=10)

# GOAL (Carnegie Hall) - northwest, label positioned closer, diagonally above-left
ax.scatter(ch_lon, ch_lat, s=1400, c='#e74c3c', edgecolor='#922b21',
          linewidth=5, marker='*', zorder=9)
# Use annotation with arrow for better connection
ax.annotate('GOAL (sᵍ)\nCarnegie Hall\n57th & 7th', 
           xy=(ch_lon, ch_lat), xytext=(ch_lon - 0.0015, ch_lat + 0.002),
           ha='right', va='bottom',
           fontsize=12, fontweight='bold',
           bbox=dict(boxstyle='round,pad=0.6', facecolor='white',
                    edgecolor='#922b21', linewidth=2.5, alpha=0.98),
           arrowprops=dict(arrowstyle='->', lw=2, color='#922b21',
                          connectionstyle='arc3,rad=0.1'),
           zorder=10)

ax.set_xlim(-74.003, -73.967)
ax.set_ylim(40.744, 40.773)
ax.set_aspect('equal')

ax.set_xlabel('Longitude', fontsize=15, fontweight='bold', color='#2c3e50')
ax.set_ylabel('Latitude', fontsize=15, fontweight='bold', color='#2c3e50')

# North arrow
ax.annotate('', xy=(-73.969, 40.771), xytext=(-73.969, 40.766),
           arrowprops=dict(arrowstyle='->', lw=6, color='#2c3e50'))
ax.text(-73.969, 40.7722, 'N', ha='center', va='bottom',
       fontsize=24, fontweight='bold', color='#2c3e50')

# Legend - placed outside plot area, in the figure but not on the graph
# Create custom legend handles
legend_elements = [
    plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='white', 
               markeredgecolor='#c0392b', markeredgewidth=2.5, markersize=12,
               label=f'{len(intersections)} intersection nodes'),
    plt.Line2D([0], [0], marker='^', color='w', markerfacecolor='#27ae60', 
               markeredgecolor='#196f3d', markeredgewidth=3, markersize=14,
               label=f'{len(corridor_cameras)} cameras')
]
# Place legend outside the plot, on the right side
ax.legend(handles=legend_elements, loc='center left', bbox_to_anchor=(1.02, 0.5),
         fontsize=13, framealpha=0.97, title='State Space Components', 
         title_fontsize=14, edgecolor='#34495e', fancybox=True, shadow=True)

# Info box
info = (f'STATE SPACE ENCODING:\n'
       f'Total nodes: {len(intersections)}\n'
       f'Node IDs: n0 to n{len(intersections)-1}\n'
       f'Camera zones: {len(corridor_cameras)}\n'
       f'Avg: {len(intersections)/len(corridor_cameras):.1f} nodes/zone\n\n'
       f'Voronoi assigns features:\n'
       f'Each intersection inherits\n'
       f'features from nearest camera')
ax.text(0.02, 0.98, info, transform=ax.transAxes,
       fontsize=11, va='top', ha='left',
       bbox=dict(boxstyle='round,pad=0.8', facecolor='#f8f9f9', 
                edgecolor='#34495e', linewidth=2.5, alpha=0.97),
       family='monospace', color='#2c3e50')

ax.grid(True, alpha=0.1, linewidth=0.6, color='#95a5a6', linestyle=':')

plt.tight_layout(rect=[0, 0, 0.95, 1])  # Leave space on right for legend
plt.savefig('state_space_map.png', dpi=300, bbox_inches='tight', facecolor='white')
print(f"\nState space map saved to state_space_map.png")
print(f"\nNode ID encoding: Sequential numbering (n0 to n{len(intersections)-1})")
print("Alternative: Could use street names such as '42nd_Park' or '57th_7th'")

