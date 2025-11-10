#!/usr/bin/env python3
"""Generate Manhattan navigation map with OSM background"""

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch
import matplotlib.image as mpimg
from PIL import Image
import urllib.request
from io import BytesIO
import numpy as np

# Grand Central: 40.7527° N, 73.9772° W  
# Carnegie Hall: 40.7651° N, 73.9799° W

# Bounding box for the map (slightly larger than our area of interest)
bbox = {
    'minlat': 40.7500,
    'maxlat': 40.7680,
    'minlon': -73.9850,
    'maxlon': -73.9740
}

# Download OSM static map
def get_osm_image(bbox, zoom=15, width=800, height=800):
    """Get OSM static map image"""
    # Use OpenStreetMap static map API
    center_lat = (bbox['minlat'] + bbox['maxlat']) / 2
    center_lon = (bbox['minlon'] + bbox['maxlon']) / 2
    
    # Staticmap API endpoint
    url = f"https://staticmap.openstreetmap.de/staticmap.php?center={center_lat},{center_lon}&zoom={zoom}&size={width}x{height}&maptype=mapnik"
    
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            img_data = response.read()
            img = Image.open(BytesIO(img_data))
            return np.array(img), True
    except Exception as e:
        print(f"Could not download map: {e}")
        return None, False

# Create figure
fig, ax = plt.subplots(figsize=(12, 10))

# Try to download map
img, success = get_osm_image(bbox)

if success and img is not None:
    # Display the map as background
    ax.imshow(img, extent=[bbox['minlon'], bbox['maxlon'], bbox['minlat'], bbox['maxlat']], 
              aspect='auto', alpha=0.7, zorder=1)
    print("Map background loaded successfully")
else:
    print("Using grid background instead")
    # Use a simple grid background
    ax.set_facecolor('#f0f0f5')
    # Draw grid
    for lat in np.linspace(bbox['minlat'], bbox['maxlat'], 10):
        ax.axhline(lat, color='#d0d0d5', linewidth=0.5, alpha=0.5)
    for lon in np.linspace(bbox['minlon'], bbox['maxlon'], 10):
        ax.axvline(lon, color='#d0d0d5', linewidth=0.5, alpha=0.5)

# Coordinates
gc_lat, gc_lon = 40.7527, -73.9772
ch_lat, ch_lon = 40.7651, -73.9799

# Plot routes
# Route 1: Baseline (East then North)
route1_lon = [gc_lon, -73.9799, -73.9799]
route1_lat = [gc_lat, gc_lat, ch_lat]
ax.plot(route1_lon, route1_lat, color='#8ec8ea', linewidth=4, linestyle='--',
        alpha=0.9, zorder=3, label='Baseline (Manhattan)', marker='o', markersize=6)

# Route 2: Learned heuristic (North then West)  
route2_lon = [gc_lon, gc_lon, ch_lon]
route2_lat = [gc_lat, ch_lat, ch_lat]
ax.plot(route2_lon, route2_lat, color='#ffb6c1', linewidth=4, linestyle='-',
        alpha=0.9, zorder=3, label='Learned heuristic', marker='o', markersize=6)

# Route 3: Alternative
route3_lon = [gc_lon, -73.9850, -73.9830, ch_lon]
route3_lat = [gc_lat, 40.7540, 40.7580, ch_lat]
ax.plot(route3_lon, route3_lat, color='#ccccff', linewidth=4, linestyle=':',
        alpha=0.9, zorder=3, label='Alternative path', marker='o', markersize=6)

# Start and goal markers
ax.scatter(gc_lon, gc_lat, s=500, color='#bdfcc9', edgecolor='#2e8b57',
           linewidth=3, zorder=5, label='Start: Grand Central')
ax.text(gc_lon, gc_lat, 'GC', ha='center', va='center', 
        fontsize=12, fontweight='bold', zorder=6)
ax.text(gc_lon, gc_lat - 0.0015, '42nd & Park', ha='center', va='top',
        fontsize=9, bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9))

ax.scatter(ch_lon, ch_lat, s=500, color='#ffb6c1', edgecolor='#dc143c',
           linewidth=3, zorder=5, label='Goal: Carnegie Hall')
ax.text(ch_lon, ch_lat, 'CH', ha='center', va='center',
        fontsize=12, fontweight='bold', zorder=6)
ax.text(ch_lon, ch_lat + 0.0015, '57th & 7th', ha='center', va='bottom',
        fontsize=9, bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9))

# North arrow
arrow_lon = -73.9750
arrow_lat = 40.7660
ax.annotate('N', xy=(arrow_lon, arrow_lat + 0.0015), xytext=(arrow_lon, arrow_lat),
            arrowprops=dict(arrowstyle='->', lw=3, color='#6495ed'),
            fontsize=16, fontweight='bold', ha='center', color='#6495ed', zorder=10)

# Set bounds
ax.set_xlim(bbox['minlon'], bbox['maxlon'])
ax.set_ylim(bbox['minlat'], bbox['maxlat'])
ax.set_aspect('equal')

# Labels
ax.set_xlabel('Longitude', fontsize=10)
ax.set_ylabel('Latitude', fontsize=10)
ax.set_title('Manhattan Navigation: Grand Central to Carnegie Hall\nReal Manhattan Street Network (North is up)', 
             fontsize=14, fontweight='bold', pad=15)

# Legend
ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.12), ncol=2,
          fontsize=10, framealpha=0.95)

plt.tight_layout()
plt.savefig('manhattan_map.png', dpi=300, bbox_inches='tight', facecolor='white')
print("Map saved to manhattan_map.png")

