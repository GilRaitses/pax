"""Draw problem space visualization with clean purple tessellation lines.

This script creates a focused visualization of the problem space (red boundary)
with deep purple Voronoi tessellation lines, fainter street grid, and start/goal
intersections as circles. This visualization is used for problem space initialization.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from scipy.spatial import Voronoi
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon

LOGGER = logging.getLogger(__name__)


def load_intersections(path: Path) -> dict:
    """Load intersection data."""
    with open(path) as f:
        return json.load(f)


def load_cameras(path: Path) -> list[dict]:
    """Load camera data."""
    with open(path) as f:
        return json.load(f)


def fetch_all_cameras_from_api() -> list[dict]:
    """Fetch all cameras from NYCTMC API."""
    try:
        # Try using the client first
        try:
            from ..data_collection.camera_client import CameraAPIClient
            from ..config import PaxSettings
            
            client = CameraAPIClient(PaxSettings())
            cameras = client.list_cameras()
            LOGGER.info("Fetched %d cameras from API via client", len(cameras))
        except Exception:
            # Fallback: fetch directly via requests
            import requests
            api_url = "https://webcams.nyctmc.org/api/cameras"
            LOGGER.info("Fetching cameras directly from %s", api_url)
            response = requests.get(api_url, timeout=30)
            response.raise_for_status()
            all_cameras = response.json()
            # Filter to only online cameras
            cameras = [cam for cam in all_cameras if cam.get("isOnline") == "true"]
            LOGGER.info("Fetched %d cameras from API directly (%d online)", len(all_cameras), len(cameras))
        
        return cameras
    except Exception as e:
        LOGGER.error("Failed to fetch cameras from API: %s", e)
        return []


def filter_cameras_in_purple_corridor(
    cameras: list[dict],
    camera_corridor_corners: dict[str, tuple[float, float]],
) -> list[dict]:
    """Filter cameras that are within the purple camera corridor bounds (including on boundary)."""
    if len(camera_corridor_corners) != 4:
        LOGGER.warning("Camera corridor corners not complete, skipping filter")
        return cameras
    
    # Create polygon from camera corridor corners
    # Order: NW -> NE -> SE -> SW -> NW
    polygon = Polygon([
        camera_corridor_corners["NW"],
        camera_corridor_corners["NE"],
        camera_corridor_corners["SE"],
        camera_corridor_corners["SW"],
    ])
    
    # Buffer polygon to include cameras on or very close to the boundary, including corners
    buffered_polygon = polygon.buffer(0.0003)  # ~33 meters at this latitude
    
    # Also explicitly check for cameras very close to corner points
    corner_tolerance = 0.0005  # ~55 meters at this latitude
    
    filtered = []
    for cam in cameras:
        lat = cam.get("latitude")
        lon = cam.get("longitude")
        if lat is None or lon is None:
            continue
        
        point = Point(lon, lat)
        
        # Check if camera is inside/on buffered polygon
        if buffered_polygon.intersects(point):
            filtered.append(cam)
            continue
        
        # Explicitly check if camera is near any corner point
        is_near_corner = False
        for corner_name, (corner_lon, corner_lat) in camera_corridor_corners.items():
            corner_point = Point(corner_lon, corner_lat)
            if point.distance(corner_point) <= corner_tolerance:
                is_near_corner = True
                break
        
        if is_near_corner:
            filtered.append(cam)
    
    LOGGER.info("Filtered %d cameras within purple corridor bounds (from %d total)", len(filtered), len(cameras))
    return filtered


def load_streets(path: Path) -> gpd.GeoDataFrame:
    """Load street centerlines."""
    streets = gpd.read_file(path)
    if streets.crs != "EPSG:4326":
        streets = streets.to_crs(epsg=4326)
    return streets[streets["Borough"] == "Manhattan"]


def find_corridor_corners_from_shapefile(streets: gpd.GeoDataFrame) -> dict[str, tuple[float, float]]:
    """Find all 4 corners by computing intersections from shapefile."""
    corners = {}
    
    # Filter to corridor area
    corridor = streets.cx[-73.995:-73.965, 40.745:40.770]
    
    # Find all geometric intersections
    for i, row1 in corridor.iterrows():
        for j, row2 in corridor.iterrows():
            if i >= j:
                continue
            
            if row1.geometry.intersects(row2.geometry):
                inter = row1.geometry.intersection(row2.geometry)
                if inter.geom_type == "Point":
                    lon, lat = inter.x, inter.y
                    name1 = str(row1.get('Street_NM', '')).lower()
                    name2 = str(row2.get('Street_NM', '')).lower()
                    
                    # Check for corners - use 61st Street for north border
                    has_8 = '8 avenue' in name1 or '8 avenue' in name2
                    has_lex = 'lexington' in name1 or 'lexington' in name2
                    has_cpw = 'central park west' in name1 or 'central park west' in name2
                    has_61 = '61' in name1 or '61' in name2
                    has_west_40 = 'west 40' in name1 or 'west 40' in name2
                    has_east_40 = 'east 40' in name1 or 'east 40' in name2
                    
                    # Find actual corners
                    # NW: Central Park West & 61st Street
                    if has_cpw and has_61 and "NW" not in corners:
                        corners["NW"] = (lon, lat)
                        LOGGER.info("Found NW: (%.6f, %.6f) from %s x %s", lon, lat, name1, name2)
                    
                    # NE: Lexington & 61st Street
                    elif has_lex and has_61 and "NE" not in corners:
                        corners["NE"] = (lon, lat)
                        LOGGER.info("Found NE: (%.6f, %.6f) from %s x %s", lon, lat, name1, name2)
                    
                    # SE: Lexington & East 40th Street
                    elif has_lex and has_east_40 and "SE" not in corners:
                        corners["SE"] = (lon, lat)
                        LOGGER.info("Found SE: (%.6f, %.6f) from %s x %s", lon, lat, name1, name2)
                    
                    # SW: 8 Avenue & West 40th Street
                    elif has_8 and has_west_40 and "SW" not in corners:
                        corners["SW"] = (lon, lat)
                        LOGGER.info("Found SW: (%.6f, %.6f) from %s x %s", lon, lat, name1, name2)
    
    return corners


def find_camera_corridor_corners_from_shapefile(streets: gpd.GeoDataFrame) -> dict[str, tuple[float, float]]:
    """Find camera corridor corners: 3rd-9th Ave (Amsterdam above 59th), 34th-66th Street."""
    corners = {}
    
    # Filter to camera corridor area (wider bounds)
    corridor = streets.cx[-74.01:-73.96, 40.74:40.78]
    
    # Find all geometric intersections
    for i, row1 in corridor.iterrows():
        for j, row2 in corridor.iterrows():
            if i >= j:
                continue
            
            if row1.geometry.intersects(row2.geometry):
                inter = row1.geometry.intersection(row2.geometry)
                if inter.geom_type == "Point":
                    lon, lat = inter.x, inter.y
                    name1 = str(row1.get('Street_NM', '')).lower()
                    name2 = str(row2.get('Street_NM', '')).lower()
                    
                    # Check for corners
                    has_3rd = '3 avenue' in name1 or '3 avenue' in name2 or 'third avenue' in name1 or 'third avenue' in name2
                    has_9th = '9 avenue' in name1 or '9 avenue' in name2 or 'ninth avenue' in name1 or 'ninth avenue' in name2
                    has_amsterdam = 'amsterdam' in name1 or 'amsterdam' in name2
                    has_columbus = 'columbus' in name1 or 'columbus' in name2  # Columbus Ave is 9th Ave above 59th
                    has_34 = '34' in name1 or '34' in name2
                    has_66 = '66' in name1 or '66' in name2
                    has_west_34 = 'west 34' in name1 or 'west 34' in name2
                    has_east_34 = 'east 34' in name1 or 'east 34' in name2
                    has_west_66 = 'west 66' in name1 or 'west 66' in name2
                    has_east_66 = 'east 66' in name1 or 'east 66' in name2
                    
                    # NW: 9th/Amsterdam/Columbus & 66th Street
                    if (has_9th or has_amsterdam or has_columbus) and (has_66 or has_west_66 or has_east_66) and "NW" not in corners:
                        corners["NW"] = (lon, lat)
                        LOGGER.info("Found camera corridor NW: (%.6f, %.6f) from %s x %s", lon, lat, name1, name2)
                    
                    # NE: 3rd Avenue & 66th Street
                    elif has_3rd and (has_66 or has_east_66) and "NE" not in corners:
                        corners["NE"] = (lon, lat)
                        LOGGER.info("Found camera corridor NE: (%.6f, %.6f) from %s x %s", lon, lat, name1, name2)
                    
                    # SE: 3rd Avenue & 34th Street
                    elif has_3rd and (has_34 or has_east_34) and "SE" not in corners:
                        corners["SE"] = (lon, lat)
                        LOGGER.info("Found camera corridor SE: (%.6f, %.6f) from %s x %s", lon, lat, name1, name2)
                    
                    # SW: 9th/Amsterdam/Columbus & 34th Street
                    elif (has_9th or has_amsterdam or has_columbus) and (has_34 or has_west_34) and "SW" not in corners:
                        corners["SW"] = (lon, lat)
                        LOGGER.info("Found camera corridor SW: (%.6f, %.6f) from %s x %s", lon, lat, name1, name2)
    
    return corners


def draw_problem_space(
    corners: dict[str, tuple[float, float]],
    cameras_for_voronoi: list[dict],
    intersections: np.ndarray,
    streets: gpd.GeoDataFrame,
    output: Path,
    bounds: tuple[float, float, float, float],
) -> None:
    """Draw problem space visualization with clean purple tessellation lines.
    
    Args:
        corners: Problem space corners (red boundary)
        cameras_for_voronoi: Cameras to use for Voronoi tessellation (all cameras in purple corridor)
        intersections: All intersections
        streets: Street centerlines
        output: Output path for the visualization
        bounds: Bounds tuple (lat_min, lat_max, lon_min, lon_max)
    """
    
    if len(corners) != 4:
        raise ValueError(f"Need all 4 corners, found {len(corners)}: {list(corners.keys())}")
    
    lat_min, lat_max, lon_min, lon_max = bounds
    
    # Manhattan street grid: align avenues vertically and streets horizontally
    center = ((lon_min + lon_max) / 2, (lat_min + lat_max) / 2)
    
    # Compute exact affine transformation matrix to align streets
    # Maps: Lexington (53.92°) -> vertical, West 40th (157.16°) -> horizontal
    lex_angle = np.radians(53.92)
    w40_angle = np.radians(157.16)
    
    # Original street directions
    lex_dir = np.array([np.cos(lex_angle), np.sin(lex_angle)])
    w40_dir = np.array([np.cos(w40_angle), np.sin(w40_angle)])
    
    # Target directions
    lex_target = np.array([0.0, 1.0])  # vertical
    w40_target = np.array([1.0, 0.0])  # horizontal
    
    # Solve for transformation matrix: T @ A = B  =>  T = B @ A^-1
    A = np.column_stack([lex_dir, w40_dir])
    B = np.column_stack([lex_target, w40_target])
    transform_matrix = B @ np.linalg.inv(A)
    
    LOGGER.info("Using exact affine transformation matrix to align streets")
    
    def transform_coords(coords_array):
        """Apply exact affine transformation, then flip x-axis to fix east/west."""
        # Translate to origin
        centered = coords_array - center
        
        # Apply transformation matrix
        transformed = (transform_matrix @ centered.T).T
        
        # Flip x-axis to fix east/west reversal
        transformed[:, 0] = -transformed[:, 0]
        
        # Translate back
        return transformed + center
    
    def transform_geometry(geom):
        """Transform shapely geometry using exact affine matrix, then flip x-axis."""
        # Translate to origin
        translated = affinity.translate(geom, -center[0], -center[1])
        
        # Apply transformation matrix
        a, b = transform_matrix[0, 0], transform_matrix[0, 1]
        d, e = transform_matrix[1, 0], transform_matrix[1, 1]
        transformed = affinity.affine_transform(translated, [a, b, d, e, 0, 0])
        
        # Flip x-axis to fix east/west reversal
        flipped = affinity.scale(transformed, xfact=-1.0, yfact=1.0, origin=(0, 0))
        
        # Translate back
        return affinity.translate(flipped, center[0], center[1])
    
    # Transform all data
    intersections_rot = transform_coords(intersections)
    camera_coords_voronoi = np.array([[float(cam["longitude"]), float(cam["latitude"])] for cam in cameras_for_voronoi])
    camera_coords_voronoi_rot = transform_coords(camera_coords_voronoi)
    
    corners_array = np.array([corners["NW"], corners["NE"], corners["SE"], corners["SW"]])
    corners_rot = transform_coords(corners_array)
    corners_rot_dict = {
        "NW": tuple(corners_rot[0]),
        "NE": tuple(corners_rot[1]),
        "SE": tuple(corners_rot[2]),
        "SW": tuple(corners_rot[3]),
    }
    
    # Transform streets
    streets_rot = streets.copy()
    streets_rot.geometry = streets_rot.geometry.apply(transform_geometry)
    
    # Create figure - frame is the red boundary (problem space)
    fig, ax = plt.subplots(figsize=(16, 12), dpi=300)
    
    # Set axis limits to red boundary (problem space)
    red_boundary_corners_rot = np.array([
        corners_rot_dict["NW"],
        corners_rot_dict["NE"],
        corners_rot_dict["SE"],
        corners_rot_dict["SW"],
    ])
    x_min, x_max = red_boundary_corners_rot[:, 0].min(), red_boundary_corners_rot[:, 0].max()
    y_min, y_max = red_boundary_corners_rot[:, 1].min(), red_boundary_corners_rot[:, 1].max()
    
    # Calculate half block distance (approximately 0.0002 degrees at this latitude)
    # A Manhattan block is roughly 0.0004 degrees
    half_block = 0.0002
    
    # Extend plot limits to include start/goal points within half block of red boundary
    # Get start/goal coordinates in transformed space
    gc_rot = transform_coords(np.array([[-73.97767660520798, 40.752118937075075]]))[0]
    ch_rot = transform_coords(np.array([[-73.98003575710818, 40.76552103342054]]))[0]
    
    # Calculate required padding to include start/goal within half block
    plot_x_min = min(x_min, gc_rot[0] - half_block, ch_rot[0] - half_block)
    plot_x_max = max(x_max, gc_rot[0] + half_block, ch_rot[0] + half_block)
    plot_y_min = min(y_min, gc_rot[1] - half_block, ch_rot[1] - half_block)
    plot_y_max = max(y_max, gc_rot[1] + half_block, ch_rot[1] + half_block)
    
    # Add small buffer for visual clarity
    x_range = plot_x_max - plot_x_min
    y_range = plot_y_max - plot_y_min
    x_pad = x_range * 0.01
    y_pad = y_range * 0.01
    
    ax.set_xlim(plot_x_min - x_pad, plot_x_max + x_pad)
    ax.set_ylim(plot_y_min - y_pad, plot_y_max + y_pad)
    ax.set_aspect("equal")
    
    # Store red boundary limits for label positioning
    red_x_min, red_x_max = x_min, x_max
    red_y_min, red_y_max = y_min, y_max
    
    # Calculate 1cm extension in plot coordinates
    # After setting plot limits, we can convert 1cm to plot coordinate units
    # 1cm = 0.3937 inches, figure width is 16 inches
    # clip_extension = (1cm / figure_width_inches) * x_range
    fig_width_inches = 16
    cm_to_inches = 0.3937
    clip_extension_cm = 1.0  # 1cm extension
    clip_extension_x = (clip_extension_cm * cm_to_inches / fig_width_inches) * x_range
    
    # Create clipping bounds: extend red boundary by 1cm on left and right
    clip_x_min = red_x_min - clip_extension_x
    clip_x_max = red_x_max + clip_extension_x
    # Keep y bounds as red boundary (no extension needed for top/bottom)
    clip_y_min = red_y_min
    clip_y_max = red_y_max
    
    # Create clipping polygon (extends 1cm beyond red boundary on left/right)
    from shapely.geometry import box
    clip_polygon = box(clip_x_min, clip_y_min, clip_x_max, clip_y_max)
    
    # Filter streets to plot area (with buffer for clipping)
    problem_streets = streets_rot.cx[plot_x_min - x_pad * 2:plot_x_max + x_pad * 2, plot_y_min - y_pad * 2:plot_y_max + y_pad * 2]
    
    # Function to clip a geometry to the extended boundary
    def clip_street_geometry(geom):
        """Clip street geometry to extend only 1cm beyond red boundary."""
        try:
            if geom.is_empty:
                return geom
            # Clip to the extended boundary polygon
            clipped = geom.intersection(clip_polygon)
            return clipped
        except Exception:
            # If clipping fails, return original geometry
            return geom
    
    # Separate major avenues from regular streets for bolder rendering
    major_avenue_names = ['8 avenue', 'broadway', '7 avenue', 'avenue of the americas', '6 avenue', 
                         '5 avenue', 'fifth avenue', 'madison', 'park avenue', 'lexington', 'central park west']
    
    major_avenues = problem_streets[
        problem_streets['Street_NM'].str.lower().str.contains('|'.join(major_avenue_names), case=False, na=False)
    ]
    regular_streets = problem_streets[
        ~problem_streets['Street_NM'].str.lower().str.contains('|'.join(major_avenue_names), case=False, na=False)
    ]
    
    # Find major cross streets (42nd, 45th, 47th, 49th, 52nd, 55th, 57th) for yellow highlighting
    cross_street_numbers = ['42', '45', '47', '49', '52', '55', '57']
    cross_street_names = []
    for num in cross_street_numbers:
        # Match various formats: "42", "42nd", "west 42", "east 42", etc.
        cross_street_names.extend([
            f'{num} street',
            f'{num} st',
            f'west {num}',
            f'east {num}',
            f'{num}nd',
            f'{num}th',
        ])
    
    major_cross_streets = problem_streets[
        problem_streets['Street_NM'].str.lower().str.contains('|'.join(cross_street_names), case=False, na=False)
    ]
    
    # Clip street geometries to extend only 1cm beyond red boundary
    regular_streets_clipped = regular_streets.copy()
    regular_streets_clipped.geometry = regular_streets_clipped.geometry.apply(clip_street_geometry)
    
    major_cross_streets_clipped = major_cross_streets.copy()
    major_cross_streets_clipped.geometry = major_cross_streets_clipped.geometry.apply(clip_street_geometry)
    
    major_avenues_clipped = major_avenues.copy()
    major_avenues_clipped.geometry = major_avenues_clipped.geometry.apply(clip_street_geometry)
    
    # Plot regular streets with fainter grey (clipped)
    regular_streets_clipped.plot(ax=ax, color="#cccccc", linewidth=1.0, alpha=0.4, zorder=1)
    
    # Plot major cross streets in yellow (clipped)
    YELLOW = "#FFD700"  # Gold/yellow
    major_cross_streets_clipped.plot(ax=ax, color=YELLOW, linewidth=3.0, alpha=0.8, zorder=2)
    
    # Find y positions of major cross streets for labeling
    # Streets run horizontally in transformed space, so we need their y positions
    cross_street_y_positions = {}
    cross_street_east_west = {}  # Track East vs West for 49th street
    
    for street_num in ['42', '45', '47', '49', '52', '55', '57']:
        # Find streets matching this number (use non-capturing group to avoid warning)
        pattern = f'(?:{street_num} street|{street_num} st|west {street_num}|east {street_num}|{street_num}nd|{street_num}th)'
        street_matches = major_cross_streets[
            major_cross_streets['Street_NM'].str.lower().str.contains(
                pattern,
                case=False, na=False, regex=True
            )
        ]
        
        if not street_matches.empty:
            # Get average y position of the street segments
            y_positions = []
            east_y_positions = []
            west_y_positions = []
            
            for _, row in street_matches.iterrows():
                geom = row.geometry
                street_name = str(row.get('Street_NM', '')).lower()
                is_east = 'east' in street_name or 'e ' in street_name
                is_west = 'west' in street_name or 'w ' in street_name
                
                if geom.geom_type == "LineString":
                    coords = np.array(list(geom.coords))
                    y_mean = np.mean(coords[:, 1])
                    y_positions.append(y_mean)
                    if is_east:
                        east_y_positions.append(y_mean)
                    if is_west:
                        west_y_positions.append(y_mean)
                elif geom.geom_type == "MultiLineString":
                    for line in geom.geoms:
                        coords = np.array(list(line.coords))
                        y_mean = np.mean(coords[:, 1])
                        y_positions.append(y_mean)
                        if is_east:
                            east_y_positions.append(y_mean)
                        if is_west:
                            west_y_positions.append(y_mean)
            
            if y_positions:
                # Store with proper suffix for labeling
                if street_num == '42':
                    cross_street_y_positions['42nd'] = np.median(y_positions)
                elif street_num == '45':
                    cross_street_y_positions['45th'] = np.median(y_positions)
                elif street_num == '47':
                    cross_street_y_positions['47th'] = np.median(y_positions)
                elif street_num == '49':
                    # For 49th, store both East and West positions if available
                    if east_y_positions and west_y_positions:
                        cross_street_y_positions['49th'] = np.median(y_positions)  # Overall median
                        cross_street_east_west['49th_east'] = np.median(east_y_positions)
                        cross_street_east_west['49th_west'] = np.median(west_y_positions)
                    else:
                        cross_street_y_positions['49th'] = np.median(y_positions)
                elif street_num == '52':
                    cross_street_y_positions['52nd'] = np.median(y_positions)
                elif street_num == '55':
                    cross_street_y_positions['55th'] = np.median(y_positions)
                elif street_num == '57':
                    cross_street_y_positions['57th'] = np.median(y_positions)
    
    # Plot major avenues with bolder lines in deep yellow (clipped)
    DEEP_YELLOW = "#B8860B"  # Dark goldenrod / deep yellow
    major_avenues_clipped.plot(ax=ax, color=DEEP_YELLOW, linewidth=2.5, alpha=0.7, zorder=2)
    
    # Add y-axis labels for cross streets on both left and right sides
    for street_label_base, y_pos in cross_street_y_positions.items():
        # Format all labels as "W. {number}th St." for left and "E. {number}th St." for right
        # Extract the number from street_label_base (e.g., "42nd" -> "42")
        street_num = street_label_base.replace('nd', '').replace('th', '').replace('rd', '').replace('st', '')
        
        # Special handling for 49th street (E vs W) - use actual East/West positions if available
        if street_label_base == '49th':
            if '49th_east' in cross_street_east_west and '49th_west' in cross_street_east_west:
                # Left side: W. 49th St.
                left_label = "W. 49th St."
                left_y_pos = cross_street_east_west['49th_west']
                # Right side: E. 49th St.
                right_label = "E. 49th St."
                right_y_pos = cross_street_east_west['49th_east']
            else:
                # Fallback to regular label if East/West not found
                left_label = "W. 49th St."
                right_label = "E. 49th St."
                left_y_pos = y_pos
                right_y_pos = y_pos
        else:
            # Regular street labels - use format "W. {number}th St." and "E. {number}th St."
            left_label = f"W. {street_label_base} St."
            right_label = f"E. {street_label_base} St."
            left_y_pos = y_pos
            right_y_pos = y_pos
        
        # Only label if within red boundary bounds
        if red_y_min <= left_y_pos <= red_y_max:
            # Left side label - match top avenue labels angle (-45 degrees)
            # Text should start from above, so use va="top" and rotation=-45
            ax.text(
                red_x_min - x_pad * 0.5,  # Left side, outside boundary
                left_y_pos,
                left_label,
                ha="right",
                va="top",  # Start from above
                fontsize=10,
                weight="bold",
                color="#666666",
                rotation=-45,  # Match top avenue labels angle (-45 degrees)
                rotation_mode="anchor",
                zorder=10,
            )
        
        if red_y_min <= right_y_pos <= red_y_max:
            # Right side label (diagonally slanted)
            # Increase offset to prevent overlap with red border
            # Add 2mm additional offset (2mm = 0.2cm)
            mm_to_cm = 0.1
            additional_offset_2mm = (2.0 * mm_to_cm * cm_to_inches / fig_width_inches) * x_range
            right_label_offset = x_pad * 1.2 + additional_offset_2mm  # Base offset + 2mm
            ax.text(
                red_x_max + right_label_offset,  # Right side, further outside boundary
                right_y_pos,
                right_label,
                ha="left",
                va="top",  # Start from above to match left side
                fontsize=10,
                weight="bold",
                color="#666666",
                rotation=-45,  # Diagonal slant (-45 degrees)
                rotation_mode="anchor",
                zorder=10,
            )
    
    # Create red boundary polygon for clipping
    red_boundary_polygon = Polygon(red_boundary_corners_rot)
    
    # Plot Voronoi tessellation with deep purple, clean lines
    vor = Voronoi(camera_coords_voronoi_rot)
    LOGGER.info("Created Voronoi tessellation with %d cameras", len(cameras_for_voronoi))
    
    # Deep purple color for tessellation lines
    DEEP_PURPLE = "#4B0082"  # Indigo/deep purple
    
    # Plot Voronoi edges, clipped to red boundary
    # Also include edges that touch or are within the boundary
    voronoi_edges_plotted = 0
    for simplex in vor.ridge_vertices:
        simplex = np.asarray(simplex)
        if np.all(simplex >= 0):  # Only finite edges
            verts = vor.vertices[simplex]
            edge_line = LineString(verts)
            
            # Check if edge intersects or touches the red boundary polygon
            try:
                # Use intersection to clip, but also check if edge touches boundary
                clipped = edge_line.intersection(red_boundary_polygon)
                if clipped.is_empty:
                    # Check if edge touches boundary (point intersection)
                    if edge_line.touches(red_boundary_polygon):
                        # Edge touches boundary, include it
                        clipped_verts = np.array(list(edge_line.coords))
                    else:
                        # Check if any part of edge is within boundary
                        if edge_line.within(red_boundary_polygon) or red_boundary_polygon.contains(edge_line):
                            clipped_verts = np.array(list(edge_line.coords))
                        else:
                            continue
                else:
                    # Handle different geometry types from intersection
                    if clipped.geom_type == "LineString":
                        clipped_verts = np.array(list(clipped.coords))
                    elif clipped.geom_type == "MultiLineString":
                        # Plot all segments, not just the longest
                        for seg in clipped.geoms:
                            seg_verts = np.array(list(seg.coords))
                            if len(seg_verts) >= 2:
                                ax.plot(
                                    seg_verts[:, 0],
                                    seg_verts[:, 1],
                                    color=DEEP_PURPLE,
                                    linewidth=2.0,
                                    alpha=0.8,
                                    zorder=5,
                                    linestyle="-",
                                    solid_capstyle="round",
                                )
                                voronoi_edges_plotted += 1
                        continue
                    elif clipped.geom_type == "Point":
                        # Single point intersection, skip
                        continue
                    else:
                        continue
            except Exception as e:
                # If clipping fails, try plotting the full edge if it's within bounds
                try:
                    if red_boundary_polygon.contains(edge_line) or edge_line.within(red_boundary_polygon):
                        clipped_verts = np.array(list(edge_line.coords))
                    else:
                        continue
                except Exception:
                    # Skip this edge
                    continue
            
            # Only plot if we have valid vertices
            if len(clipped_verts) >= 2:
                # Single clean line, not fuzzy
                # Use higher zorder so Voronoi lines appear above Central Park fill
                ax.plot(
                    clipped_verts[:, 0],
                    clipped_verts[:, 1],
                    color=DEEP_PURPLE,
                    linewidth=2.0,
                    alpha=0.8,
                    zorder=5,  # Higher zorder to appear above park fill and label
                    linestyle="-",
                    solid_capstyle="round",
                )
                voronoi_edges_plotted += 1
    
    LOGGER.info("Plotted %d Voronoi edges", voronoi_edges_plotted)
    
    # Draw red boundary frame
    perimeter = [
        corners_rot_dict["NW"],
        corners_rot_dict["NE"],
        corners_rot_dict["SE"],
        corners_rot_dict["SW"],
        corners_rot_dict["NW"],
    ]
    perimeter_array = np.array(perimeter)
    ax.plot(
        perimeter_array[:, 0],
        perimeter_array[:, 1],
        color="#e74c3c",
        linewidth=4.0,
        alpha=0.9,
        zorder=5,
        label="Problem space boundary",
    )
    
    # Plot START and GOAL as circles
    # Grand Central: Park Avenue x East 42 Street
    gc_lon, gc_lat = -73.97767660520798, 40.752118937075075
    # Carnegie Hall: 7 Avenue x West 57 Street
    ch_lon, ch_lat = -73.98003575710818, 40.76552103342054
    
    # gc_rot and ch_rot already computed above
    
    # Plot as circles
    ax.scatter(
        gc_rot[0], gc_rot[1],
        s=800,
        c="#3498db",
        edgecolor="#1a5276",
        linewidth=3,
        marker="o",
        zorder=9,
        label="START (Grand Central)",
    )
    ax.scatter(
        ch_rot[0], ch_rot[1],
        s=800,
        c="#e74c3c",
        edgecolor="#922b21",
        linewidth=3,
        marker="o",
        zorder=9,
        label="GOAL (Carnegie Hall)",
    )
    
    # Add labels for START and GOAL from the sides, offset away from map
    # Use larger offset to avoid overlapping with axis labels
    label_offset_x = x_range * 0.15  # 15% of x range for significant offset
    
    # START label from right side with connecting line
    # Calculate label position first, then extend plot limits to accommodate it
    start_label_x = red_x_max + label_offset_x * 2  # Extend well past red boundary
    start_label_y = gc_rot[1]
    
    # GOAL label from left side with connecting line
    goal_label_x = red_x_min - label_offset_x * 2  # Extend well past red boundary
    goal_label_y = ch_rot[1]
    
    # Extend plot limits to include labels and lines
    extended_x_min = min(plot_x_min - x_pad, goal_label_x - label_offset_x * 0.5)
    extended_x_max = max(plot_x_max + x_pad, start_label_x + label_offset_x * 0.5)
    ax.set_xlim(extended_x_min, extended_x_max)
    
    # Draw lines from circles to labels (extended to reach labels)
    # Draw on top of everything with high zorder
    ax.plot(
        [gc_rot[0], start_label_x],
        [start_label_y, start_label_y],
        color="#3498db",
        linewidth=2.5,
        linestyle="--",
        alpha=0.8,
        zorder=15,  # Very high zorder to draw on top
    )
    
    ax.text(
        start_label_x,
        start_label_y,
        "START",
        ha="left",
        va="center",
        fontsize=14,
        weight="bold",
        color="#3498db",
        zorder=16,  # Even higher zorder for text
    )
    
    ax.plot(
        [ch_rot[0], goal_label_x],
        [goal_label_y, goal_label_y],
        color="#e74c3c",
        linewidth=2.5,
        linestyle="--",
        alpha=0.8,
        zorder=15,  # Very high zorder to draw on top
    )
    
    ax.text(
        goal_label_x,
        goal_label_y,
        "GOAL",
        ha="right",
        va="center",
        fontsize=14,
        weight="bold",
        color="#e74c3c",
        zorder=16,  # Even higher zorder for text
    )
    
    # Compute true north direction in transformed coordinates
    # True north in geographic coordinates: direction vector (0, 1) in (lon, lat) space
    # After transformation: transform_matrix @ [0, 1]^T
    # After x-axis flip: [-transform_matrix[0,1], transform_matrix[1,1]]
    north_dir_geo = np.array([0.0, 1.0])  # True north (increasing latitude)
    north_dir_transformed = transform_matrix @ north_dir_geo
    # Apply x-axis flip
    north_dir_transformed[0] = -north_dir_transformed[0]
    # Compute angle in transformed space
    north_angle = np.arctan2(north_dir_transformed[1], north_dir_transformed[0])
    north_angle_deg = np.degrees(north_angle)
    
    LOGGER.info("True north angle in transformed space: %.2f degrees", north_angle_deg)
    
    # Add compass arrow outside frame (top center) - rotated to point to true north
    arrow_length = 0.03
    arrow_dx = arrow_length * np.cos(north_angle)
    arrow_dy = arrow_length * np.sin(north_angle)
    
    ax.annotate(
        "",
        xy=(0.5 + arrow_dx, 1.02 + arrow_dy),
        xycoords="axes fraction",
        xytext=(0.5, 1.02),
        arrowprops=dict(arrowstyle="->", lw=3, color="#2c3e50"),
    )
    ax.text(
        0.5 + arrow_dx * 1.2,
        1.02 + arrow_dy * 1.2,
        "N",
        ha="center",
        va="center",
        transform=ax.transAxes,
        fontsize=20,
        weight="bold",
        color="#2c3e50",
    )
    
    # Find major avenues that cross the problem space and label them along x-axis
    # Avenues run vertically (north-south) in transformed space, so they have constant x values
    # Major avenues: 8th, Broadway, 7th, 6th, 5th, Madison, Park, Lexington, CPW
    avenue_names = {
        '8 avenue': '8th Ave',
        'broadway': 'Broadway',
        '7 avenue': '7th Ave',
        'avenue of the americas': '6th Ave',
        '6 avenue': '6th Ave',
        '5 avenue': '5th Ave',
        'fifth avenue': '5th Ave',
        'madison': 'Madison',
        'park avenue': 'Park',
        'lexington': 'Lexington',
        'central park west': 'Central Park West',
    }
    
    # Find avenue segments in problem space and get their x positions
    # Use intersection with red boundary lines for accurate positioning
    from shapely.geometry import LineString as ShapelyLineString
    
    # Create horizontal lines at top and bottom of red boundary
    bottom_boundary_line = ShapelyLineString([(red_x_min - 0.001, red_y_min), (red_x_max + 0.001, red_y_min)])
    top_boundary_line = ShapelyLineString([(red_x_min - 0.001, red_y_max), (red_x_max + 0.001, red_y_max)])
    
    avenue_x_positions = {}
    for _, street_row in problem_streets.iterrows():
        street_name = str(street_row.get('Street_NM', '')).lower()
        geom = street_row.geometry
        
        # Check if this is a major avenue
        for key, label in avenue_names.items():
            if key in street_name:
                # Find intersection with bottom boundary line (for bottom labels)
                # and top boundary line (for top labels)
                intersections_bottom = []
                intersections_top = []
                
                if geom.geom_type == "LineString":
                    if geom.intersects(bottom_boundary_line):
                        inter = geom.intersection(bottom_boundary_line)
                        if inter.geom_type == "Point":
                            intersections_bottom.append(inter.x)
                        elif inter.geom_type == "MultiPoint":
                            for pt in inter.geoms:
                                intersections_bottom.append(pt.x)
                    
                    if geom.intersects(top_boundary_line):
                        inter = geom.intersection(top_boundary_line)
                        if inter.geom_type == "Point":
                            intersections_top.append(inter.x)
                        elif inter.geom_type == "MultiPoint":
                            for pt in inter.geoms:
                                intersections_top.append(pt.x)
                
                elif geom.geom_type == "MultiLineString":
                    for line in geom.geoms:
                        if line.intersects(bottom_boundary_line):
                            inter = line.intersection(bottom_boundary_line)
                            if inter.geom_type == "Point":
                                intersections_bottom.append(inter.x)
                            elif inter.geom_type == "MultiPoint":
                                for pt in inter.geoms:
                                    intersections_bottom.append(pt.x)
                        
                        if line.intersects(top_boundary_line):
                            inter = line.intersection(top_boundary_line)
                            if inter.geom_type == "Point":
                                intersections_top.append(inter.x)
                            elif inter.geom_type == "MultiPoint":
                                for pt in inter.geoms:
                                    intersections_top.append(pt.x)
                
                # Use median intersection x position (handles multiple intersections)
                # Store both bottom and top positions separately for accurate labeling
                if intersections_bottom:
                    x_pos_bottom = np.median(intersections_bottom)
                    # Store bottom position
                    avenue_x_positions[f"{label}_bottom"] = x_pos_bottom
                    # Also store as default if not already set
                    if label not in avenue_x_positions:
                        avenue_x_positions[label] = x_pos_bottom
                
                if intersections_top:
                    x_pos_top = np.median(intersections_top)
                    # Store top position separately
                    avenue_x_positions[f"{label}_top"] = x_pos_top
                    # Use top position as default if bottom wasn't found
                    if label not in avenue_x_positions:
                        avenue_x_positions[label] = x_pos_top
                
                break
    
        # Label avenues along bottom x-axis (diagonal slant)
        # Calculate label height for proper padding
        label_fontsize = 10
        # Offset to place labels outside red boundary (not overlapping)
        label_offset = y_range * 0.015  # Small offset below/above red boundary
        
        if avenue_x_positions:
            # Import MPLPolygon for park patches
            from matplotlib.patches import Polygon as MPLPolygon
            
            # Sort by x position (west to east)
            sorted_avenues = sorted(avenue_x_positions.items(), key=lambda x: x[1])
            
            # Track which avenues should be labeled as "Central Park" on top
            central_park_x_positions = []
            if '6th Ave' in avenue_x_positions:
                central_park_x_positions.append(avenue_x_positions['6th Ave'])
            if '7th Ave' in avenue_x_positions:
                central_park_x_positions.append(avenue_x_positions['7th Ave'])
            # Use median x position for Central Park label
            central_park_x = np.median(central_park_x_positions) if central_park_x_positions else None
            
            # Label along bottom x-axis with diagonal rotation
            # Central Park West on bottom should be labeled as "8th Ave"
            for label_key, x_pos in sorted_avenues:
                # Extract clean label name (remove _bottom or _top suffix)
                if label_key.endswith('_bottom'):
                    label = label_key[:-7]  # Remove "_bottom"
                elif label_key.endswith('_top'):
                    continue  # Skip top-only labels on bottom
                else:
                    label = label_key
                
                # Special handling: Central Park West on bottom should be labeled as "8th Ave"
                display_label = label
                if label == 'Central Park West':
                    display_label = '8th Ave'
                
                # Use bottom intersection position if available, otherwise use default position
                bottom_key = f"{label}_bottom"
                if bottom_key in avenue_x_positions:
                    x_pos = avenue_x_positions[bottom_key]
                elif label in avenue_x_positions:
                    # Use default position if no bottom-specific position found
                    x_pos = avenue_x_positions[label]
                else:
                    # Skip if no position found at all
                    continue
                
                # Only label if within red boundary bounds
                if red_x_min <= x_pos <= red_x_max:
                    # Offset below red boundary so label doesn't overlap
                    # For rotation=45°, to have last letter touch axis line:
                    # Position text slightly below red_y_min with ha="right", va="bottom"
                    ax.text(
                        x_pos,
                        red_y_min - label_offset,  # Offset below red boundary
                        display_label,  # Use display label (8th Ave for CPW on bottom)
                        ha="right",  # Right-align so last letter is at x_pos
                        va="bottom",  # Bottom-align
                        fontsize=label_fontsize,
                        weight="bold",
                        color="#666666",
                        rotation=45,  # Diagonal slant
                        rotation_mode="anchor",
                    )
            
            # Label avenues along top x-axis (diagonal slant)
            # Exclude 8th Ave and Broadway from top labels
            # Use "Central Park" for 6th/7th on top axis (single label, not separate)
            # Process all labels, not just those with _top suffix
            processed_top_labels = set()
            
            # First, collect all unique labels that should appear on top
            all_top_labels = set()
            for label_key, x_pos in sorted_avenues:
                # Extract clean label name
                if label_key.endswith('_top'):
                    label = label_key[:-4]
                elif label_key.endswith('_bottom'):
                    label = label_key[:-7]
                else:
                    label = label_key
                
                # Skip excluded labels
                if label in ['8th Ave', 'Broadway', '6th Ave', '7th Ave']:
                    continue
                
                all_top_labels.add(label)
            
            # Ensure Lexington is always included if it exists in avenue_names
            if 'Lexington' in avenue_names.values() and 'Lexington' not in all_top_labels:
                # Check if Lexington exists in the streets data
                lex_exists = any('lexington' in str(name).lower() for name in problem_streets['Street_NM'])
                if lex_exists:
                    all_top_labels.add('Lexington')
                    LOGGER.info("Added Lexington to top labels (was missing from sorted_avenues)")
            
            # Now label each one, ensuring we get the right position
            # Sort by x position for consistent ordering
            top_labels_with_positions = []
            for label in all_top_labels:
                # Use top intersection position if available, otherwise use default position
                top_key = f"{label}_top"
                if top_key in avenue_x_positions:
                    x_pos = avenue_x_positions[top_key]
                elif label in avenue_x_positions:
                    # Use default position if no top-specific position found
                    x_pos = avenue_x_positions[label]
                else:
                    # For Lexington specifically, try to find it even if not in positions
                    if label == 'Lexington':
                        # Try to find Lexington avenue in the major_avenues (already filtered and transformed)
                        lex_streets = major_avenues[
                            major_avenues['Street_NM'].str.lower().str.contains('lexington', case=False, na=False)
                        ]
                        if not lex_streets.empty:
                            # Get x positions from intersections with top boundary
                            lex_x_positions = []
                            for _, row in lex_streets.iterrows():
                                geom = row.geometry
                                if geom.intersects(top_boundary_line):
                                    inter = geom.intersection(top_boundary_line)
                                    if inter.geom_type == "Point":
                                        lex_x_positions.append(inter.x)
                                    elif inter.geom_type == "MultiPoint":
                                        for pt in inter.geoms:
                                            lex_x_positions.append(pt.x)
                                    elif inter.geom_type == "LineString":
                                        # If intersection is a line, get the x coordinate
                                        lex_x_positions.append(inter.coords[0][0])
                            if lex_x_positions:
                                x_pos = np.median(lex_x_positions)
                                LOGGER.info("Found Lexington top position manually: %.6f", x_pos)
                            else:
                                # Try using the median x position of all Lexington segments
                                lex_x_all = []
                                for _, row in lex_streets.iterrows():
                                    geom = row.geometry
                                    if geom.geom_type == "LineString":
                                        coords = np.array(list(geom.coords))
                                        lex_x_all.append(np.median(coords[:, 0]))
                                    elif geom.geom_type == "MultiLineString":
                                        for line in geom.geoms:
                                            coords = np.array(list(line.coords))
                                            lex_x_all.append(np.median(coords[:, 0]))
                                if lex_x_all:
                                    x_pos = np.median(lex_x_all)
                                    LOGGER.info("Found Lexington top position from median x: %.6f", x_pos)
                                else:
                                    LOGGER.warning("Lexington found in streets but no usable position")
                                    continue
                        else:
                            LOGGER.warning("Lexington not found in streets data")
                            continue
                    else:
                        # Skip if no position found at all
                        LOGGER.warning("No position found for top label: %s (available keys: %s)", label, list(avenue_x_positions.keys())[:10])
                        continue
                
                top_labels_with_positions.append((label, x_pos))
            
            # Sort by x position and label
            top_labels_with_positions.sort(key=lambda x: x[1])
            
            for label, x_pos in top_labels_with_positions:
                # For Lexington, be more lenient with bounds check since it might be slightly outside
                # For other labels, check if within red boundary bounds
                if label == 'Lexington':
                    # Allow Lexington if it's close to the boundary (within 2% of x_range)
                    tolerance = x_range * 0.02
                    if red_x_min - tolerance <= x_pos <= red_x_max + tolerance:
                        ax.text(
                            x_pos,
                            red_y_max + label_offset,  # Offset above red boundary
                            label,  # Use clean label name without suffix
                            ha="right",  # Right-align so last letter is at x_pos
                            va="top",  # Top-align
                            fontsize=label_fontsize,
                            weight="bold",
                            color="#666666",
                            rotation=-45,  # Diagonal slant (opposite direction)
                            rotation_mode="anchor",
                        )
                        LOGGER.info("Rendered Lexington label at x=%.6f (red_x_min=%.6f, red_x_max=%.6f)", x_pos, red_x_min, red_x_max)
                elif red_x_min <= x_pos <= red_x_max:
                    ax.text(
                        x_pos,
                        red_y_max + label_offset,  # Offset above red boundary
                        label,  # Use clean label name without suffix
                        ha="right",  # Right-align so last letter is at x_pos
                        va="top",  # Top-align
                        fontsize=label_fontsize,
                        weight="bold",
                        color="#666666",
                        rotation=-45,  # Diagonal slant (opposite direction)
                        rotation_mode="anchor",
                    )
        
        # Label "Central Park" inside the park area, centered horizontally and vertically
        # Central Park is between 5th Ave (east) and Central Park West (west) in the visible area
        # Find the bounds of Central Park within the red boundary
        cpw_x = None
        fifth_ave_x = None
        
        # Look for Central Park West (not CPW)
        if 'Central Park West_top' in avenue_x_positions:
            cpw_x = avenue_x_positions['Central Park West_top']
        elif 'Central Park West' in avenue_x_positions:
            cpw_x = avenue_x_positions['Central Park West']
        
        if '5th Ave_top' in avenue_x_positions:
            fifth_ave_x = avenue_x_positions['5th Ave_top']
        elif '5th Ave' in avenue_x_positions:
            fifth_ave_x = avenue_x_positions['5th Ave']
        
        # If we have both boundaries, fill Central Park area with green and add label
        if cpw_x is not None and fifth_ave_x is not None:
            # Central Park is between CPW (west) and 5th Ave (east)
            # Central Park spans from approximately 59th Street to 110th Street
            # In our problem space (40th to 61st), we show the southern portion
            # Create a polygon for the visible portion of Central Park
            # Park starts around 59th street, which is approximately (59-40)/(61-40) = 19/21 ≈ 90.5% up
            park_y_start = red_y_min + (red_y_max - red_y_min) * (19/21)  # 59th street
            park_y_end = red_y_max  # Top of red boundary (61st street)
            
            # Create Central Park polygon in transformed coordinates (already transformed)
            # cpw_x and fifth_ave_x are already in transformed space
            from matplotlib.patches import Polygon as MPLPolygon
            park_patch = MPLPolygon([
                (cpw_x, park_y_start),  # SW corner
                (cpw_x, park_y_end),    # NW corner
                (fifth_ave_x, park_y_end),  # NE corner
                (fifth_ave_x, park_y_start),  # SE corner
            ],
                facecolor="#2ecc71",  # Green color
                edgecolor="#27ae60",  # Darker green edge
                linewidth=1.0,
                alpha=0.4,  # Semi-transparent so Voronoi lines show through
                zorder=1,  # Low zorder - behind streets and Voronoi lines
            )
            ax.add_patch(park_patch)
            
            # Position label in the park area, shifted slightly to the right
            park_x_center = (cpw_x + fifth_ave_x) / 2
            # Shift right by 10% of the park width
            park_width = fifth_ave_x - cpw_x
            park_x_label = park_x_center + (park_width * 0.10)  # Shift 10% to the right
            
            # Move 3 blocks higher (from 57th to 60th street)
            # Red boundary spans from 40th to 61st street (21 blocks)
            # 60th street = (60-40)/(61-40) = 20/21 ≈ 95.2% up from bottom
            park_y_center = red_y_min + (red_y_max - red_y_min) * 0.952  # ~60th street (3 blocks higher than 57th)
            
            # Only label if within red boundary bounds
            if red_x_min <= park_x_label <= red_x_max and red_y_min <= park_y_center <= red_y_max:
                ax.text(
                    park_x_label,
                    park_y_center,
                    'Central Park',
                    ha="center",  # Center horizontally
                    va="center",  # Center vertically
                    fontsize=label_fontsize + 2,  # Slightly larger
                    weight="bold",
                    color="#2c3e50",  # Darker color for visibility
                    rotation=0,  # No rotation - horizontal text
                    rotation_mode="anchor",
                    zorder=4,  # Above park fill but below Voronoi lines
                )
        
        # Add Bryant Park: green fill and label
        # Bryant Park is between 40th-42nd St (south-north) and 5th-6th Ave (east-west)
        # In transformed space: streets are horizontal (y-axis), avenues are vertical (x-axis)
        fifth_ave_x_bp = None
        sixth_ave_x_bp = None
        
        # Use bottom positions for Bryant Park (it's at the bottom of the problem space)
        if '5th Ave_bottom' in avenue_x_positions:
            fifth_ave_x_bp = avenue_x_positions['5th Ave_bottom']
        elif '5th Ave' in avenue_x_positions:
            fifth_ave_x_bp = avenue_x_positions['5th Ave']
        
        if '6th Ave_bottom' in avenue_x_positions:
            sixth_ave_x_bp = avenue_x_positions['6th Ave_bottom']
        elif '6th Ave' in avenue_x_positions:
            sixth_ave_x_bp = avenue_x_positions['6th Ave']
        
        # Bryant Park spans from 40th to 42nd Street
        # Red boundary spans from 40th to 61st street (21 blocks)
        # 40th street = 0% up from bottom, 42nd street = (42-40)/(61-40) = 2/21 ≈ 9.5% up
        bp_y_start = red_y_min  # 40th street (bottom of red boundary)
        bp_y_end = red_y_min + (red_y_max - red_y_min) * (2/21)  # 42nd street
        
        # If we have both boundaries, fill Bryant Park area with green and add label
        if fifth_ave_x_bp is not None and sixth_ave_x_bp is not None:
            # Bryant Park is between 5th Ave (east) and 6th Ave (west)
            # Create Bryant Park polygon
            bp_patch = MPLPolygon([
                (sixth_ave_x_bp, bp_y_start),  # SW corner (6th Ave, 40th St)
                (sixth_ave_x_bp, bp_y_end),    # NW corner (6th Ave, 42nd St)
                (fifth_ave_x_bp, bp_y_end),     # NE corner (5th Ave, 42nd St)
                (fifth_ave_x_bp, bp_y_start),   # SE corner (5th Ave, 40th St)
            ],
                facecolor="#2ecc71",  # Green color (same as Central Park)
                edgecolor="#27ae60",  # Darker green edge
                linewidth=1.0,
                alpha=0.4,  # Semi-transparent so Voronoi lines show through
                zorder=1,  # Low zorder - behind streets and Voronoi lines
            )
            ax.add_patch(bp_patch)
            
            # Position label in the center of Bryant Park, nudged 0.6cm + 1mm to the left
            bp_x_center = (fifth_ave_x_bp + sixth_ave_x_bp) / 2
            bp_y_center = (bp_y_start + bp_y_end) / 2
            
            # Calculate 0.6cm + 1mm offset in plot coordinates (same calculation as clip_extension_x)
            nudge_cm = 0.6
            mm_to_cm = 0.1
            additional_nudge_1mm = (1.0 * mm_to_cm * cm_to_inches / fig_width_inches) * x_range
            nudge_x = (nudge_cm * cm_to_inches / fig_width_inches) * x_range + additional_nudge_1mm
            bp_x_label = bp_x_center - nudge_x  # Move left (subtract)
            
            # Only label if within red boundary bounds
            if red_x_min <= bp_x_label <= red_x_max and red_y_min <= bp_y_center <= red_y_max:
                ax.text(
                    bp_x_label,
                    bp_y_center,
                    'Bryant Park',
                    ha="center",  # Center horizontally
                    va="center",  # Center vertically
                    fontsize=label_fontsize + 2,  # Slightly larger
                    weight="bold",
                    color="#2c3e50",  # Darker color for visibility
                    rotation=0,  # No rotation - horizontal text
                    rotation_mode="anchor",
                    zorder=4,  # Above park fill but below Voronoi lines
                )
    
    # Remove axes ticks but keep spines for clean look
    ax.set_xticks([])
    ax.set_yticks([])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.spines["left"].set_visible(False)
    
    # Add plot title - position it high enough to avoid overlap with labels
    # Get current plot limits to position title above everything
    current_xlim = ax.get_xlim()
    current_ylim = ax.get_ylim()
    title_y = current_ylim[1] + (current_ylim[1] - current_ylim[0]) * 0.12  # 12% above top
    title_x = (current_xlim[0] + current_xlim[1]) / 2  # Center horizontally
    
    ax.text(
        title_x,
        title_y,
        "Problem Space: Multi-Scale Coverage Zones",
        ha="center",
        va="bottom",
        fontsize=16,
        weight="bold",
        color="#2c3e50",
        zorder=20,  # Very high zorder
    )
    
    # Adjust y limits to include title
    ax.set_ylim(current_ylim[0], title_y + (current_ylim[1] - current_ylim[0]) * 0.05)
    
    # Save with padding to accommodate labels
    plt.tight_layout(pad=2.0)  # Add padding for labels
    plt.savefig(output, dpi=300, bbox_inches="tight", pad_inches=0.3, facecolor="white")
    LOGGER.info("Saved problem space visualization to %s", output)
    plt.close()


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Draw problem space visualization")
    parser.add_argument(
        "--intersections",
        type=Path,
        default=Path("data/geojson/intersections.json"),
        help="Path to intersections JSON file",
    )
    parser.add_argument(
        "--cameras",
        type=Path,
        default=Path("data/cameras.json"),
        help="Path to cameras JSON file (fallback if API fails)",
    )
    parser.add_argument(
        "--streets",
        type=Path,
        default=Path("data/shapefiles/dcm/DCM_StreetCenterLine.shp"),
        help="Path to street centerlines shapefile",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/problem_space.png"),
        help="Output path for the visualization",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )
    
    args = parser.parse_args(argv)
    
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(levelname)s: %(message)s",
    )
    
    # Load data
    LOGGER.info("Loading intersections from %s", args.intersections)
    intersections_data = load_intersections(args.intersections)
    intersections = np.array(intersections_data["coordinates"])
    LOGGER.info("Loaded %d intersections", len(intersections))
    
    # Load or fetch cameras
    LOGGER.info("Fetching cameras from NYCTMC API...")
    cameras = fetch_all_cameras_from_api()
    if not cameras:
        LOGGER.warning("Failed to fetch cameras from API. Falling back to file: %s", args.cameras)
        cameras = load_cameras(args.cameras)
    LOGGER.info("Loaded %d cameras", len(cameras))
    
    LOGGER.info("Loading streets from %s", args.streets)
    streets = load_streets(args.streets)
    LOGGER.info("Loaded %d street segments", len(streets))
    
    # Find problem space corners (red boundary)
    LOGGER.info("Finding problem space corners from shapefile...")
    corners = find_corridor_corners_from_shapefile(streets)
    if len(corners) != 4:
        LOGGER.error("Failed to find all 4 problem space corners. Found: %s", list(corners.keys()))
        return 1
    
    # Find camera corridor corners (purple boundary) for filtering cameras
    LOGGER.info("Finding camera corridor corners from shapefile...")
    camera_corridor_corners = find_camera_corridor_corners_from_shapefile(streets)
    if len(camera_corridor_corners) != 4:
        LOGGER.warning("Failed to find all 4 camera corridor corners. Found: %s", list(camera_corridor_corners.keys()))
        LOGGER.warning("Will use all cameras for Voronoi tessellation")
        cameras_for_voronoi = cameras
    else:
        # Filter cameras to purple corridor
        cameras_for_voronoi = filter_cameras_in_purple_corridor(cameras, camera_corridor_corners)
    
    # Compute bounds from problem space corners
    lons = [c[0] for c in corners.values()]
    lats = [c[1] for c in corners.values()]
    lon_min, lon_max = min(lons), max(lons)
    lat_min, lat_max = min(lats), max(lats)
    bounds = (lat_min, lat_max, lon_min, lon_max)
    
    # Draw problem space visualization
    draw_problem_space(
        corners=corners,
        cameras_for_voronoi=cameras_for_voronoi,
        intersections=intersections,
        streets=streets,
        output=args.output,
        bounds=bounds,
    )
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

