#!/usr/bin/env python3
"""Create map visualizations with color-coded paths showing perceptual stress"""

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle
from matplotlib.collections import LineCollection
import matplotlib.colors as mcolors
import contextily as cx
from shapely.geometry import Point, LineString
import os
from dotenv import load_dotenv
import requests
from io import BytesIO
from PIL import Image

# Load environment variables
load_dotenv()
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')

def get_google_static_map(center_lat, center_lon, zoom=15, width=640, height=640):
    """Fetch a static map from Google Maps API"""
    if not GOOGLE_MAPS_API_KEY:
        return None
    
    base_url = "https://maps.googleapis.com/maps/api/staticmap"
    params = {
        'center': f'{center_lat},{center_lon}',
        'zoom': zoom,
        'size': f'{width}x{height}',
        'scale': 2,
        'maptype': 'roadmap',
        'style': 'feature:poi|visibility:off',  # Reduce clutter
        'style': 'feature:transit|visibility:off',
        'key': GOOGLE_MAPS_API_KEY
    }
    
    try:
        response = requests.get(base_url, params=params)
        if response.status_code == 200:
            return Image.open(BytesIO(response.content))
    except Exception as e:
        print(f"Failed to fetch Google Maps: {e}")
    return None

# Start and goal coordinates
gc_lat, gc_lon = 40.7527, -73.9772  # Grand Central, 42nd & Park
ch_lat, ch_lon = 40.7651, -73.9799  # Carnegie Hall, 57th & 7th

def get_directions_with_waypoints(origin, destination, waypoints):
    """Get actual route from Google Directions API with waypoints"""
    if not GOOGLE_MAPS_API_KEY:
        return None
    
    base_url = "https://maps.googleapis.com/maps/api/directions/json"
    
    # Format waypoints
    waypoints_str = '|'.join([f'{lat},{lon}' for lat, lon in waypoints])
    
    params = {
        'origin': f'{origin[0]},{origin[1]}',
        'destination': f'{destination[0]},{destination[1]}',
        'waypoints': waypoints_str,
        'mode': 'walking',
        'key': GOOGLE_MAPS_API_KEY
    }
    
    try:
        response = requests.get(base_url, params=params)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'OK':
                # Extract all coordinates from the route
                route_coords = []
                for leg in data['routes'][0]['legs']:
                    for step in leg['steps']:
                        # Decode polyline
                        polyline = step['polyline']['points']
                        decoded = decode_polyline(polyline)
                        route_coords.extend(decoded)
                return route_coords
        print(f"Directions API error: {response.status_code}")
    except Exception as e:
        print(f"Error getting directions: {e}")
    
    return None

def decode_polyline(polyline_str):
    """Decode Google's polyline format to lat/lon coordinates"""
    index, lat, lng = 0, 0, 0
    coordinates = []
    changes = {'latitude': 0, 'longitude': 0}
    
    while index < len(polyline_str):
        for unit in ['latitude', 'longitude']:
            shift, result = 0, 0
            
            while True:
                byte = ord(polyline_str[index]) - 63
                index += 1
                result |= (byte & 0x1f) << shift
                shift += 5
                if not byte >= 0x20:
                    break
            
            if result & 1:
                changes[unit] = ~(result >> 1)
            else:
                changes[unit] = result >> 1
        
        lat += changes['latitude']
        lng += changes['longitude']
        
        coordinates.append((lat / 1e5, lng / 1e5))
    
    return coordinates

def assign_colors_to_route(coords, route_type):
    """Assign stress colors along the route using position-based gradients"""
    if not coords:
        return []

    n = len(coords)
    colored_route = []

    def gradient(progress, stops):
        for threshold, color in stops:
            if progress <= threshold:
                return color
        return stops[-1][1]

    if route_type == 'baseline':
        # Green leaving GC, yellow near Bryant Park, then orange → red → crimson up 7th Ave
        stops = [
            (0.20, '#2ecc71'),   # green
            (0.35, '#f1c40f'),   # yellow
            (0.60, '#e67e22'),   # orange
            (0.80, '#c0392b'),   # red
            (1.00, '#7b241c'),   # deep crimson
        ]
    elif route_type == 'learned':
        stops = [
            (1.00, '#27ae60'),   # keep entire path mint green (lowest stress)
        ]
    elif route_type == 'alternative':
        # Pleasant up Park, then stress climbs along Central Park South and 7th Ave
        stops = [
            (0.40, '#27ae60'),   # green
            (0.60, '#9acd32'),   # yellow-green
            (0.75, '#f1c40f'),   # yellow
            (0.88, '#e67e22'),   # orange
            (1.00, '#c0392b'),   # red
        ]
    else:
        stops = [(1.00, '#27ae60')]

    for i, (lat, lon) in enumerate(coords):
        progress = i / max(n - 1, 1)
        color = gradient(progress, stops)
        colored_route.append((lon, lat, color))

    return colored_route

# Get actual routes from Google Directions API
print("Fetching routes from Google Directions API...")

# BASELINE: Grand Central → 42nd/6th (Bryant Park) → 42nd/7th → Carnegie Hall
baseline_waypoints = [
    (40.7536, -73.9832),  # 42nd & 6th (Bryant Park)
]
baseline_coords = get_directions_with_waypoints(
    (gc_lat, gc_lon), (ch_lat, ch_lon), baseline_waypoints
)
baseline_route = assign_colors_to_route(baseline_coords, 'baseline') if baseline_coords else None

# LEARNED: Grand Central → 45th/Park → 45th/Madison → 55th/Madison → 55th/6th → 57th/6th → Carnegie Hall
learned_waypoints = [
    (40.7545, -73.9772),  # 45th & Park
    (40.7545, -73.9785),  # 45th & Madison
    (40.7633, -73.9785),  # 55th & Madison
    (40.7633, -73.9810),  # 55th & 6th
    (40.7651, -73.9810),  # 57th & 6th
]
learned_coords = get_directions_with_waypoints(
    (gc_lat, gc_lon), (ch_lat, ch_lon), learned_waypoints
)
learned_route = assign_colors_to_route(learned_coords, 'learned') if learned_coords else None

# ALTERNATIVE: Grand Central → 59th/Park → 59th/7th (Central Park South) → Carnegie Hall
alternative_waypoints = [
    (40.7678, -73.9772),  # 59th & Park
    (40.7678, -73.9799),  # 59th & 7th
]
alternative_coords = get_directions_with_waypoints(
    (gc_lat, gc_lon), (ch_lat, ch_lon), alternative_waypoints
)
alternative_route = assign_colors_to_route(alternative_coords, 'alternative') if alternative_coords else None

def plot_route_with_gradient(ax, route, title):
    """Plot a route with color gradient on Google Maps Static API (NO WATERMARKS!)"""
    # Extract coordinates and colors
    lons = [r[0] for r in route]
    lats = [r[1] for r in route]
    colors = [r[2] for r in route]
    
    # Calculate center and bounds
    center_lon = (min(lons) + max(lons)) / 2
    center_lat = (min(lats) + max(lats)) / 2
    
    # Calculate path bounds first (with padding)
    path_lon_min, path_lon_max = min(lons), max(lons)
    path_lat_min, path_lat_max = min(lats), max(lats)
    
    path_lon_range = path_lon_max - path_lon_min
    path_lat_range = path_lat_max - path_lat_min
    padding_lon = path_lon_range * 0.1
    padding_lat = path_lat_range * 0.1
    
    # Bounds for the map view
    view_lon_min = path_lon_min - padding_lon
    view_lon_max = path_lon_max + padding_lon
    view_lat_min = path_lat_min - padding_lat
    view_lat_max = path_lat_max + padding_lat
    
    # Calculate center and size for Google Maps request
    view_center_lon = (view_lon_min + view_lon_max) / 2
    view_center_lat = (view_lat_min + view_lat_max) / 2
    
    # Get Google Maps static image
    if GOOGLE_MAPS_API_KEY:
        base_url = "https://maps.googleapis.com/maps/api/staticmap"
        
        # Use zoom level that will cover the view bounds
        # Estimate zoom based on the larger dimension
        view_lon_range = view_lon_max - view_lon_min
        view_lat_range = view_lat_max - view_lat_min
        max_range = max(view_lon_range, view_lat_range)
        
        # Rough zoom calculation: larger range = lower zoom
        if max_range > 0.02:  # > ~2km
            zoom = 14
        elif max_range > 0.01:  # > ~1km
            zoom = 15
        else:
            zoom = 16
        
        params = {
            'center': f'{view_center_lat},{view_center_lon}',
            'zoom': zoom,
            'size': '640x640',
            'scale': 2,
            'maptype': 'roadmap',
            'key': GOOGLE_MAPS_API_KEY
        }
        
        try:
            response = requests.get(base_url, params=params)
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
                
                # Calculate the bounds of the image in lat/lon
                meters_per_pixel = 156543.03392 * np.cos(view_center_lat * np.pi / 180) / (2 ** zoom)
                
                # Image is 1280x1280 pixels (640*2 for scale=2)
                img_width, img_height = img.size
                
                # Calculate bounds in degrees
                lat_range = (img_height / 2) * meters_per_pixel / 111320
                lon_range = (img_width / 2) * meters_per_pixel / (111320 * np.cos(view_center_lat * np.pi / 180))
                
                extent = [
                    view_center_lon - lon_range,
                    view_center_lon + lon_range,
                    view_center_lat - lat_range,
                    view_center_lat + lat_range
                ]
                
                # Display the Google Maps image
                ax.imshow(img, extent=extent, aspect='auto', zorder=1)
                
                # Plot path as CONTINUOUS LINE (no dots!)
                # Create segments for LineCollection
                segments = []
                segment_colors = []
                for i in range(len(lons) - 1):
                    segments.append([(lons[i], lats[i]), (lons[i+1], lats[i+1])])
                    segment_colors.append(colors[i])
                
                # Use LineCollection for smooth continuous line
                lc = LineCollection(segments, colors=segment_colors, linewidths=8, 
                                   alpha=0.9, zorder=4, capstyle='round', joinstyle='round')
                ax.add_collection(lc)
                
                # Start marker (Grand Central) - small circle, no white border
                circle_scale = max(view_lon_range, view_lat_range)
                circle_size = circle_scale * 0.012
                ax.add_patch(Circle((lons[0], lats[0]), circle_size, 
                                   color='#27ae60', ec='#1e8449', linewidth=2, zorder=7))
                ax.text(lons[0], lats[0], 'GC', ha='center', va='center', 
                       fontsize=10, fontweight='bold', color='white', zorder=8)
                
                # Goal marker (Carnegie Hall) - small circle, no white border
                ax.add_patch(Circle((lons[-1], lats[-1]), circle_size, 
                                   color='#e74c3c', ec='#c0392b', linewidth=2, zorder=7))
                ax.text(lons[-1], lats[-1], 'CH', ha='center', va='center', 
                       fontsize=10, fontweight='bold', color='white', zorder=8)
                
                # Use the view bounds we calculated earlier
                ax.set_xlim(view_lon_min, view_lon_max)
                ax.set_ylim(view_lat_min, view_lat_max)
                ax.set_aspect('equal', adjustable='box')
                
                print(f"✓ Using Google Maps (no watermarks!)")
                
            else:
                print(f"Google Maps API error: {response.status_code}")
                raise Exception("Fallback to CartoDB")
                
        except Exception as e:
            print(f"Error with Google Maps, falling back: {e}")
            # Fallback to CartoDB if Google Maps fails
            use_cartodb_fallback(ax, lons, lats, colors)
    else:
        print("No API key, using CartoDB fallback")
        use_cartodb_fallback(ax, lons, lats, colors)
    
    # Clean axes
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axis('off')
    
    return ax

def use_cartodb_fallback(ax, lons, lats, colors):
    """Fallback to CartoDB basemap if Google Maps unavailable"""
    route_points = [Point(lon, lat) for lon, lat in zip(lons, lats)]
    route_gdf = gpd.GeoDataFrame(geometry=route_points, crs='EPSG:4326')
    route_gdf_merc = route_gdf.to_crs(epsg=3857)
    
    # Calculate tight bounds around path
    path_lon_min, path_lon_max = min(lons), max(lons)
    path_lat_min, path_lat_max = min(lats), max(lats)
    
    path_lon_range = path_lon_max - path_lon_min
    path_lat_range = path_lat_max - path_lat_min
    padding_lon = path_lon_range * 0.1
    padding_lat = path_lat_range * 0.1
    
    ax.set_xlim(path_lon_min - padding_lon, path_lon_max + padding_lon)
    ax.set_ylim(path_lat_min - padding_lat, path_lat_max + padding_lat)
    ax.set_aspect('equal', adjustable='box')
    
    cx.add_basemap(ax, crs=route_gdf_merc.crs, source=cx.providers.CartoDB.Voyager, 
                   zoom=16, alpha=0.88)
    
    merc_coords = [(pt.x, pt.y) for pt in route_gdf_merc.geometry]
    
    # Use LineCollection for continuous line (no dots!)
    segments = []
    segment_colors = []
    for i in range(len(merc_coords) - 1):
        segments.append([merc_coords[i], merc_coords[i+1]])
        segment_colors.append(colors[i])
    
    lc = LineCollection(segments, colors=segment_colors, linewidths=7, 
                       alpha=0.9, zorder=4, capstyle='round', joinstyle='round')
    ax.add_collection(lc)
    
    gc_point_merc = route_gdf_merc.geometry.iloc[0]
    ch_point_merc = route_gdf_merc.geometry.iloc[-1]
    
    circle_scale = max(path_lon_range, path_lat_range)
    circle_size = circle_scale * 0.012
    ax.add_patch(Circle((gc_point_merc.x, gc_point_merc.y), circle_size, 
                       color='#27ae60', ec='#1e8449', linewidth=2, zorder=7))
    ax.text(gc_point_merc.x, gc_point_merc.y, 'GC', ha='center', va='center', 
           fontsize=10, fontweight='bold', color='white', zorder=8)
    
    ax.add_patch(Circle((ch_point_merc.x, ch_point_merc.y), circle_size, 
                       color='#e74c3c', ec='#c0392b', linewidth=2, zorder=7))
    ax.text(ch_point_merc.x, ch_point_merc.y, 'CH', ha='center', va='center', 
           fontsize=10, fontweight='bold', color='white', zorder=8)

# Check if routes were fetched successfully
if not all([baseline_route, learned_route, alternative_route]):
    print("\n❌ Failed to fetch routes from Google Directions API")
    print("Check your API key and make sure Directions API is enabled")
    exit(1)

print(f"✓ Baseline route: {len(baseline_route)} points")
print(f"✓ Learned route: {len(learned_route)} points")
print(f"✓ Alternative route: {len(alternative_route)} points")

# Create the three maps
routes = [
    (baseline_route, 'Baseline', 'baseline_path_map.png'),
    (learned_route, 'Learned', 'learned_path_map.png'),
    (alternative_route, 'Alternative', 'alternative_path_map.png'),
]

print("\nGenerating maps with actual Google routes...")
for route, title, filename in routes:
    # Calculate aspect ratio from route bounds
    lons = [r[0] for r in route]
    lats = [r[1] for r in route]
    
    lon_range = max(lons) - min(lons)
    lat_range = max(lats) - min(lats)
    
    # Account for padding (10% on each side = 20% total)
    lon_range_padded = lon_range * 1.2
    lat_range_padded = lat_range * 1.2
    
    # Calculate aspect ratio (width/height)
    # Convert to meters for accurate calculation
    # At Manhattan's latitude (~40.75), 1 degree lat ≈ 111km, 1 degree lon ≈ 85km
    width_m = lon_range_padded * 85000  # approximate meters
    height_m = lat_range_padded * 111000  # approximate meters
    
    aspect_ratio = width_m / height_m if height_m > 0 else 1.0
    
    # Target height for LaTeX is 1.8in, calculate width to match aspect ratio
    target_height = 1.8
    target_width = target_height * aspect_ratio
    
    # Ensure reasonable bounds (consistent sizing across columns)
    target_width = max(1.8, min(target_width, 2.6))
    
    fig, ax = plt.subplots(figsize=(target_width, target_height))
    plot_route_with_gradient(ax, route, title)
    
    plt.tight_layout(pad=0)
    plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white', pad_inches=0.01)
    plt.close()
    print(f"✓ Saved {filename} (aspect ratio: {aspect_ratio:.2f}, size: {target_width:.2f}x{target_height:.2f}in)")

print("\n🎯 All path maps with REAL GOOGLE DIRECTIONS generated successfully!")
