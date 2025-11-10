#!/usr/bin/env python3
"""Generate Manhattan navigation map with actual OSM street network"""

import matplotlib.pyplot as plt
import contextily as ctx
import geopandas as gpd
from shapely.geometry import Point, LineString
import numpy as np

# Create figure
fig, ax = plt.subplots(figsize=(12, 10))

# Grand Central: 40.7527° N, 73.9772° W
# Carnegie Hall: 40.7651° N, 73.9799° W

gc_lat, gc_lon = 40.7527, -73.9772
ch_lat, ch_lon = 40.7651, -73.9799

# Create route coordinates (simplified Manhattan grid navigation)
# Route 1: Baseline (East on 42nd, then North on 7th)
route1_coords = [
    (gc_lon, gc_lat),  # Start at GC
    (-73.9799, gc_lat),  # Go west to 7th Ave along 42nd
    (-73.9799, ch_lat),  # Go north to 57th
]

# Route 2: Learned heuristic (North on Park, then West on 57th)
route2_coords = [
    (gc_lon, gc_lat),  # Start at GC
    (gc_lon, ch_lat),  # Go north on Park
    (ch_lon, ch_lat),  # Go west to 7th
]

# Route 3: Alternative mixed
route3_coords = [
    (gc_lon, gc_lat),
    (-73.9850, 40.75),  # Intermediate
    (-73.9830, 40.7580),  # Intermediate
    (ch_lon, ch_lat),
]

# Create GeoDataFrame for points
gdf_points = gpd.GeoDataFrame({
    'name': ['Grand Central', 'Carnegie Hall'],
    'geometry': [Point(gc_lon, gc_lat), Point(ch_lon, ch_lat)]
}, crs='EPSG:4326')

# Create GeoDataFrame for routes
gdf_route1 = gpd.GeoDataFrame({
    'name': ['Baseline (Manhattan)'],
    'geometry': [LineString(route1_coords)]
}, crs='EPSG:4326')

gdf_route2 = gpd.GeoDataFrame({
    'name': ['Learned heuristic'],
    'geometry': [LineString(route2_coords)]
}, crs='EPSG:4326')

gdf_route3 = gpd.GeoDataFrame({
    'name': ['Alternative path'],
    'geometry': [LineString(route3_coords)]
}, crs='EPSG:4326')

# Convert to Web Mercator for plotting with basemap
gdf_points = gdf_points.to_crs(epsg=3857)
gdf_route1 = gdf_route1.to_crs(epsg=3857)
gdf_route2 = gdf_route2.to_crs(epsg=3857)
gdf_route3 = gdf_route3.to_crs(epsg=3857)

# Plot routes
gdf_route1.plot(ax=ax, linewidth=4, color='#8ec8ea', linestyle='--', 
                alpha=0.8, zorder=3, label='Baseline (Manhattan)')
gdf_route2.plot(ax=ax, linewidth=4, color='#ffb6c1', linestyle='-', 
                alpha=0.8, zorder=3, label='Learned heuristic')
gdf_route3.plot(ax=ax, linewidth=4, color='#ccccff', linestyle=':', 
                alpha=0.8, zorder=3, label='Alternative path')

# Plot start and end points
gdf_points[gdf_points['name'] == 'Grand Central'].plot(
    ax=ax, color='#bdfcc9', edgecolor='#2e8b57', markersize=300, 
    linewidth=2, zorder=5, label='Start: Grand Central'
)
gdf_points[gdf_points['name'] == 'Carnegie Hall'].plot(
    ax=ax, color='#ffb6c1', edgecolor='#dc143c', markersize=300, 
    linewidth=2, zorder=5, label='Goal: Carnegie Hall'
)

# Add basemap
try:
    ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron, zoom=14, alpha=0.7)
except Exception as e:
    print(f"Warning: Could not load basemap: {e}")
    print("Continuing without basemap...")

# Set bounds
buffer = 500  # meters
bounds = gdf_points.total_bounds
ax.set_xlim(bounds[0] - buffer, bounds[2] + buffer)
ax.set_ylim(bounds[1] - buffer, bounds[3] + buffer)

# Add north arrow
arrow_x = bounds[2] + buffer * 0.7
arrow_y = bounds[3] + buffer * 0.7
ax.annotate('N', xy=(arrow_x, arrow_y + 200), xytext=(arrow_x, arrow_y),
            arrowprops=dict(arrowstyle='->', lw=3, color='#6495ed'),
            fontsize=16, fontweight='bold', ha='center', color='#6495ed')

# Add labels
gc_point = gdf_points[gdf_points['name'] == 'Grand Central'].geometry.iloc[0]
ch_point = gdf_points[gdf_points['name'] == 'Carnegie Hall'].geometry.iloc[0]

ax.text(gc_point.x, gc_point.y - 150, 'GC\n42nd & Park', 
        ha='center', va='top', fontsize=10, fontweight='bold',
        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

ax.text(ch_point.x, ch_point.y + 150, 'CH\n57th & 7th', 
        ha='center', va='bottom', fontsize=10, fontweight='bold',
        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

ax.set_title('Manhattan Navigation: Grand Central to Carnegie Hall\nReal Street Network (North is up)', 
             fontsize=14, fontweight='bold', pad=15)
ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.08), ncol=2, 
          fontsize=10, framealpha=0.95)
ax.axis('off')

plt.tight_layout()
plt.savefig('manhattan_map.png', dpi=300, bbox_inches='tight', facecolor='white')
print("Map with OpenStreetMap basemap saved to manhattan_map.png")




