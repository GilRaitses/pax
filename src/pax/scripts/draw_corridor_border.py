"""Draw corridor border on Voronoi map - simple approach."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from scipy.spatial import Voronoi
from shapely.geometry import Point, Polygon

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
        
        # Log cameras on 3rd Avenue and Upper East Side for verification
        import re
        third_ave_cameras = []
        ues_cameras = []
        for cam in cameras:
            name = cam.get('name', '').upper()
            lat = cam.get('latitude', 0)
            lon = cam.get('longitude', 0)
            
            # Check 3rd Avenue (34th to 66th) - be more specific
            # Look for "3 AVE", "3RD AVE", "THIRD AVE" at start or after @
            third_ave_pattern = r'(^|@\s*)(3\s*(RD|ST)?\s*(AVE|AVENUE)|THIRD\s+(AVE|AVENUE))'
            if re.search(third_ave_pattern, name):
                if 40.748 <= lat <= 40.773:
                    third_ave_cameras.append(cam.get('name'))
            
            # Also check by coordinates - 3rd Avenue is roughly at -73.97 longitude
            if -73.98 <= lon <= -73.96 and 40.748 <= lat <= 40.773:
                if cam.get('name') not in [c for c in third_ave_cameras]:
                    # Might be 3rd Ave even if name doesn't match
                    pass
            
            # Check Upper East Side (59th & 5th to 3rd & 66th)
            # Bounds: 40.762 (59th) to 40.773 (66th), -73.98 (5th) to -73.96 (3rd)
            if 40.762 <= lat <= 40.773 and -73.98 <= lon <= -73.96:
                ues_cameras.append(cam.get('name'))
        
        if third_ave_cameras:
            LOGGER.info("Found %d cameras on 3rd Avenue (34th-66th): %s", len(third_ave_cameras), ', '.join(third_ave_cameras[:5]))
        else:
            LOGGER.warning("No cameras found on 3rd Avenue (34th-66th) by name - checking coordinates...")
            # Check by coordinates
            third_ave_by_coords = []
            for cam in cameras:
                lat = cam.get('latitude', 0)
                lon = cam.get('longitude', 0)
                if -73.98 <= lon <= -73.96 and 40.748 <= lat <= 40.773:
                    third_ave_by_coords.append(cam.get('name'))
            if third_ave_by_coords:
                LOGGER.info("Found %d cameras near 3rd Avenue coordinates (34th-66th): %s", len(third_ave_by_coords), ', '.join(third_ave_by_coords[:5]))
        
        if ues_cameras:
            LOGGER.info("Found %d cameras in Upper East Side (59th & 5th to 3rd & 66th): %s", len(ues_cameras), ', '.join(ues_cameras[:5]))
        else:
            LOGGER.warning("No cameras found in Upper East Side area - may be missing cameras!")
        
        return cameras
    except Exception as e:
        LOGGER.warning("Failed to fetch cameras from API: %s. Using fallback.", e)
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
    # Increased buffer to catch cameras on boundary lines and at corners (about 30-40 meters)
    buffered_polygon = polygon.buffer(0.0003)  # ~33 meters at this latitude
    
    # Also explicitly check for cameras very close to corner points
    # Corner tolerance: ~50 meters to catch cameras at corners
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
        # This catches corner cameras that might be slightly outside the polygon
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
    from shapely.geometry import Point
    
    corners = {}
    reference_points = {}  # Store related intersections for computing NW
    
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


def find_corridor_corners(intersections_data: dict) -> dict[str, tuple[float, float]]:
    """Find the 4 corners of the corridor perimeter from intersection data.
    
    Returns dict with keys: NW, NE, SE, SW and values: (lon, lat)
    """
    corners = {}
    
    # Look for actual intersections in the data
    for key, info in intersections_data["intersections"].items():
        streets = [s.lower() for s in info.get("streets", [])]
        lon, lat = info["coord"]
        
        has_8th = any("8 avenue" in s for s in streets)
        has_amsterdam = any("amsterdam" in s for s in streets)
        has_lex = any("lexington" in s for s in streets)
        has_west_59 = any("west 59" in s for s in streets)
        has_east_59 = any("east 59" in s for s in streets)
        has_west_40 = any("west 40" in s for s in streets)
        has_east_40 = any("east 40" in s for s in streets)
        
        # NW: West 59th & Amsterdam Avenue (8th Ave becomes Amsterdam above 59th)
        if (has_amsterdam or has_8th) and has_west_59:
            corners["NW"] = (lon, lat)
            LOGGER.info("Found NW (West 59 & Amsterdam/8th): (%.6f, %.6f) from %s", lon, lat, info.get("streets", []))
        
        # NE: Lexington & East 59th Street
        elif has_lex and has_east_59:
            corners["NE"] = (lon, lat)
            LOGGER.info("Found NE (Lex & East 59): (%.6f, %.6f) from %s", lon, lat, info.get("streets", []))
        
        # SE: Lexington & East 40th Street
        elif has_lex and has_east_40:
            corners["SE"] = (lon, lat)
            LOGGER.info("Found SE (Lex & East 40): (%.6f, %.6f) from %s", lon, lat, info.get("streets", []))
        
        # SW: 8 Avenue & West 40th Street
        elif has_8th and has_west_40:
            corners["SW"] = (lon, lat)
            LOGGER.info("Found SW (8 Ave & West 40): (%.6f, %.6f) from %s", lon, lat, info.get("streets", []))
    
    if len(corners) != 4:
        LOGGER.error("Only found %d/4 corners: %s", len(corners), list(corners.keys()))
        raise ValueError(f"Could not find all 4 corners. Found: {list(corners.keys())}")
    
    return corners


def draw_corridor_border(
    corners: dict[str, tuple[float, float]],
    cameras: list[dict],
    cameras_for_voronoi: list[dict],
    intersections: np.ndarray,
    streets: gpd.GeoDataFrame,
    output: Path,
    bounds: tuple[float, float, float, float],
    camera_corridor_corners: dict[str, tuple[float, float]] | None = None,
) -> None:
    """Draw the Voronoi map with corridor border, rotated to align streets with frame."""
    
    if len(corners) != 4:
        raise ValueError(f"Need all 4 corners, found {len(corners)}: {list(corners.keys())}")
    
    lat_min, lat_max, lon_min, lon_max = bounds
    
    # Manhattan street grid: align avenues vertically and streets horizontally
    # Strategy: 
    # 1. Rotate to make Lexington Avenue vertical (90°)
    # 2. Shear to make West 40th Street horizontal (0°)
    center = ((lon_min + lon_max) / 2, (lat_min + lat_max) / 2)
    
    from shapely import affinity
    
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
        # shapely affine_transform: [a, b, d, e, xoff, yoff]
        # where [a b] [x]   [xoff]
        #       [d e] [y] + [yoff]
        a, b = transform_matrix[0, 0], transform_matrix[0, 1]
        d, e = transform_matrix[1, 0], transform_matrix[1, 1]
        transformed = affinity.affine_transform(translated, [a, b, d, e, 0, 0])
        
        # Flip x-axis to fix east/west reversal
        flipped = affinity.scale(transformed, xfact=-1.0, yfact=1.0, origin=(0, 0))
        
        # Translate back
        return affinity.translate(flipped, center[0], center[1])
    
    # Transform all data using combined transformation
    intersections_rot = transform_coords(intersections)
    # Use cameras_for_voronoi for Voronoi tessellation
    camera_coords_voronoi = np.array([[float(cam["longitude"]), float(cam["latitude"])] for cam in cameras_for_voronoi])
    camera_coords_voronoi_rot = transform_coords(camera_coords_voronoi)
    # Use all cameras for plotting
    camera_coords_all = np.array([[float(cam["longitude"]), float(cam["latitude"])] for cam in cameras])
    camera_coords_all_rot = transform_coords(camera_coords_all)
    
    corners_array = np.array([corners["NW"], corners["NE"], corners["SE"], corners["SW"]])
    corners_rot = transform_coords(corners_array)
    corners_rot_dict = {
        "NW": tuple(corners_rot[0]),
        "NE": tuple(corners_rot[1]),
        "SE": tuple(corners_rot[2]),
        "SW": tuple(corners_rot[3]),
    }
    
    # Transform streets using combined transformation
    streets_rot = streets.copy()
    streets_rot.geometry = streets_rot.geometry.apply(transform_geometry)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(22, 18), dpi=300)
    
    # Compute transformed bounds early (needed for Voronoi filtering and label placement)
    bounds_corners = np.array([
        [lon_min, lat_min],
        [lon_min, lat_max],
        [lon_max, lat_min],
        [lon_max, lat_max],
    ])
    bounds_transformed = transform_coords(bounds_corners)
    
    # Plot streets (rotated)
    streets_rot.plot(ax=ax, color="#2c3e50", linewidth=1.8, alpha=0.7, zorder=2)
    
    # Plot Voronoi tessellation (using ALL cameras in purple corridor bounds)
    # This includes cameras both inside and outside the red problem space.
    # This ensures intersections near the red boundary edges are correctly assigned
    # to their nearest camera for Pareto front score computation.
    # cameras_for_voronoi contains all cameras in purple corridor (82 cameras)
    vor = Voronoi(camera_coords_voronoi_rot)
    LOGGER.info("Created Voronoi tessellation with %d cameras (all in purple corridor bounds)", len(cameras_for_voronoi))
    
    # Plot Voronoi edges, clipped to purple corridor boundary
    # This ensures cells properly divide around edge cameras while respecting the purple border
    from shapely.geometry import LineString
    
    # Create purple corridor polygon in transformed coordinates for clipping
    if camera_corridor_corners and len(camera_corridor_corners) == 4:
        purple_corners_array = np.array([
            camera_corridor_corners["NW"],
            camera_corridor_corners["NE"],
            camera_corridor_corners["SE"],
            camera_corridor_corners["SW"],
        ])
        purple_corners_transformed = transform_coords(purple_corners_array)
        purple_polygon_transformed = Polygon(purple_corners_transformed)
    else:
        purple_polygon_transformed = None
    
    # Plot Voronoi edges, clipping them at purple border
    for simplex in vor.ridge_vertices:
        simplex = np.asarray(simplex)
        if np.all(simplex >= 0):  # Only finite edges (not infinite rays)
            verts = vor.vertices[simplex]
            edge_line = LineString(verts)
            
            # Clip edge to purple polygon if available
            if purple_polygon_transformed:
                try:
                    clipped = edge_line.intersection(purple_polygon_transformed)
                    if clipped.is_empty:
                        continue
                    # Handle different geometry types
                    if clipped.geom_type == "LineString":
                        clipped_verts = np.array(list(clipped.coords))
                    elif clipped.geom_type == "MultiLineString":
                        # Take the longest segment
                        clipped_verts = np.array(list(max(clipped.geoms, key=lambda g: g.length).coords))
                    else:
                        continue
                except Exception:
                    # If clipping fails, use original edge
                    clipped_verts = verts
            else:
                clipped_verts = verts
            
            # Only plot if we have valid vertices
            if len(clipped_verts) >= 2:
                for width, alpha in [(12, 0.05), (10, 0.08), (8, 0.1), (6, 0.12), (4, 0.15), (2, 0.18)]:
                    ax.plot(
                        clipped_verts[:, 0],
                        clipped_verts[:, 1],
                        color="#ffd700",
                        linewidth=width,
                        alpha=alpha,
                        zorder=3,
                        linestyle="-",
                        solid_capstyle="round",
                    )
    
    # Draw corridor perimeter (using rotated coordinates): NW -> NE -> SE -> SW -> NW
    perimeter = [
        corners_rot_dict["NW"],
        corners_rot_dict["NE"],
        corners_rot_dict["SE"],
        corners_rot_dict["SW"],
        corners_rot_dict["NW"],  # Close the loop
    ]
    perimeter_array = np.array(perimeter)
    
    ax.plot(
        perimeter_array[:, 0],
        perimeter_array[:, 1],
        color="#e74c3c",
        linewidth=4,
        linestyle="-",
        marker="o",
        markersize=8,
        markerfacecolor="#e74c3c",
        markeredgecolor="#c0392b",
        markeredgewidth=2,
        zorder=8,
        label="Problem space (40th-61st, Lex-8th/CPW)",
    )
    
    # Draw camera corridor in eggplant purple if provided
    if camera_corridor_corners and len(camera_corridor_corners) == 4:
        camera_corners_array = np.array([
            camera_corridor_corners["NW"],
            camera_corridor_corners["NE"],
            camera_corridor_corners["SE"],
            camera_corridor_corners["SW"],
            camera_corridor_corners["NW"],  # Close the loop
        ])
        camera_corners_transformed = transform_coords(camera_corners_array)
        
        ax.plot(
            camera_corners_transformed[:, 0],
            camera_corners_transformed[:, 1],
            color="#6B3FA0",  # Eggplant purple
            linewidth=4,
            linestyle="-",
            marker="o",
            markersize=8,
            markerfacecolor="#6B3FA0",
            markeredgecolor="#4A2C6B",
            markeredgewidth=2,
            zorder=7,
            label="Camera corridor (34th-66th, 3rd-9th/Amsterdam)",
        )
    
    LOGGER.info("Drew perimeter: NW (%.6f, %.6f) -> NE (%.6f, %.6f) -> SE (%.6f, %.6f) -> SW (%.6f, %.6f)",
                corners["NW"][0], corners["NW"][1],
                corners["NE"][0], corners["NE"][1],
                corners["SE"][0], corners["SE"][1],
                corners["SW"][0], corners["SW"][1])
    
    # Plot intersection nodes (rotated)
    ax.scatter(
        intersections_rot[:, 0],
        intersections_rot[:, 1],
        s=55,
        c="white",
        edgecolor="#e74c3c",
        linewidth=1.5,
        zorder=6,
        alpha=0.95,
        label=f"{len(intersections)} intersection nodes",
    )
    
    # Plot cameras (rotated)
    # Separate cameras into those in purple corridor and others
    purple_corridor_cameras = []
    other_cameras = []
    
    if camera_corridor_corners and len(camera_corridor_corners) == 4:
        # Create polygon for purple corridor
        purple_polygon = Polygon([
            camera_corridor_corners["NW"],
            camera_corridor_corners["NE"],
            camera_corridor_corners["SE"],
            camera_corridor_corners["SW"],
        ])
        
        # Buffer polygon to include cameras on or very close to boundary, including corners
        # Increased buffer to catch cameras on boundary lines and at corners
        buffered_purple_polygon = purple_polygon.buffer(0.0003)
        
        for i, cam in enumerate(cameras):
            lat = cam.get("latitude")
            lon = cam.get("longitude")
            if lat is None or lon is None:
                continue
            
            point = Point(lon, lat)
            # Use intersects to catch cameras inside, on boundary, or very close to boundary
            if buffered_purple_polygon.intersects(point):
                purple_corridor_cameras.append((i, cam))
            else:
                other_cameras.append((i, cam))
    else:
        # If no purple corridor, all cameras are "other"
        other_cameras = [(i, cam) for i, cam in enumerate(cameras)]
    
    # Plot cameras outside purple corridor (smaller, lighter)
    if other_cameras:
        other_indices = [i for i, _ in other_cameras]
        other_coords_rot = camera_coords_all_rot[other_indices]
        ax.scatter(
            other_coords_rot[:, 0],
            other_coords_rot[:, 1],
            s=120,
            c="#95a5a6",
            edgecolor="#7f8c8d",
            linewidth=1.5,
            zorder=6,
            alpha=0.6,
            marker="^",
        )
    
    # Plot cameras in purple corridor (larger, brighter, with numbers)
    if purple_corridor_cameras:
        purple_indices = [i for i, _ in purple_corridor_cameras]
        purple_coords_rot = camera_coords_all_rot[purple_indices]
        
        ax.scatter(
            purple_coords_rot[:, 0],
            purple_coords_rot[:, 1],
            s=200,
            c="#2ecc71",
            edgecolor="#27ae60",
            linewidth=2.5,
            zorder=7,
            alpha=0.95,
            label=f"{len(purple_corridor_cameras)} cameras in corridor",
            marker="^",
        )
        
        # Add numbers to cameras in purple corridor
        for num, (orig_idx, cam) in enumerate(purple_corridor_cameras, start=1):
            cam_coord_rot = camera_coords_all_rot[orig_idx]
            ax.text(
                cam_coord_rot[0],
                cam_coord_rot[1],
                str(num),
                fontsize=8,
                weight="bold",
                ha="center",
                va="center",
                color="white",
                zorder=8,
                bbox=dict(boxstyle="circle,pad=0.15", facecolor="#27ae60", edgecolor="white", linewidth=1),
            )
    else:
        # Fallback: plot all cameras if no purple corridor filtering
        ax.scatter(
            camera_coords_all_rot[:, 0],
            camera_coords_all_rot[:, 1],
            s=180,
            c="#2ecc71",
            edgecolor="#27ae60",
            linewidth=2.5,
            zorder=7,
            alpha=0.95,
            label=f"{len(cameras)} cameras",
            marker="^",
        )
    
    # Plot START and GOAL (transformed)
    # bounds_transformed already computed above
    # Use correct intersection coordinates from shapefile
    gc_lon, gc_lat = -73.97767660520798, 40.752118937075075  # Park Avenue x East 42 Street
    ch_lon, ch_lat = -73.98003575710818, 40.76552103342054  # 7 Avenue x West 57 Street
    
    gc_rot = transform_coords(np.array([[gc_lon, gc_lat]]))[0]
    ch_rot = transform_coords(np.array([[ch_lon, ch_lat]]))[0]
    
    # Plot stars
    ax.scatter(gc_rot[0], gc_rot[1], s=1400, c="#3498db", edgecolor="#1a5276", linewidth=5, marker="*", zorder=9)
    ax.scatter(ch_rot[0], ch_rot[1], s=1400, c="#e74c3c", edgecolor="#922b21", linewidth=5, marker="*", zorder=9)
    
    # Get axis limits to place labels outside frame
    x_min, x_max = bounds_transformed[:, 0].min(), bounds_transformed[:, 0].max()
    y_min, y_max = bounds_transformed[:, 1].min(), bounds_transformed[:, 1].max()
    x_range = x_max - x_min
    y_range = y_max - y_min
    
    # Place START label outside frame (bottom right) with line pointing to star
    gc_label_x = x_max + 0.01 * x_range
    gc_label_y = y_min + 0.15 * y_range
    
    # Draw line from label to star
    ax.plot([gc_label_x, gc_rot[0]], [gc_label_y, gc_rot[1]], 
            color="#3498db", linewidth=2, linestyle="--", alpha=0.7, zorder=8)
    
    ax.text(
        gc_label_x, gc_label_y,
        "START (s₀)\nGrand Central\n42nd & Park",
        ha="left",
        va="bottom",
        fontsize=12,
        weight="bold",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor="#3498db", linewidth=2),
        zorder=10,
    )
    
    # Place GOAL label outside frame (top left) with line pointing to star
    ch_label_x = x_min - 0.01 * x_range
    ch_label_y = y_max - 0.15 * y_range
    
    # Draw line from label to star
    ax.plot([ch_label_x, ch_rot[0]], [ch_label_y, ch_rot[1]], 
            color="#e74c3c", linewidth=2, linestyle="--", alpha=0.7, zorder=8)
    
    ax.text(
        ch_label_x, ch_label_y,
        "GOAL (sᵍ)\nCarnegie Hall\n57th & 7th",
        ha="right",
        va="top",
        fontsize=12,
        weight="bold",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor="#e74c3c", linewidth=2),
        zorder=10,
    )
    
    # Set axis labels and title
    ax.set_xlabel("Longitude (transformed)", fontsize=14, weight="bold")
    ax.set_ylabel("Latitude (transformed)", fontsize=14, weight="bold")
    
    # Set axis limits (bounds_transformed already computed above)
    ax.set_xlim(bounds_transformed[:, 0].min(), bounds_transformed[:, 0].max())
    ax.set_ylim(bounds_transformed[:, 1].min(), bounds_transformed[:, 1].max())
    
    # Add compass (pointing to actual north) - place outside frame at top center
    # Use axes coordinates for positioning outside the frame
    arrow_base_ax = (0.5, 1.015)  # Center top, slightly above frame
    arrow_tip_ax = (0.5, 1.045)   # Further above
    
    # Draw arrow using annotation with axes coordinates
    ax.annotate(
        "",
        xy=arrow_tip_ax,
        xytext=arrow_base_ax,
        xycoords='axes fraction',
        arrowprops=dict(arrowstyle="->", lw=4, color="black"),
        zorder=15,
    )
    ax.text(0.5, 1.015, "N", 
            fontsize=28, weight="bold", ha="center", va="bottom", 
            transform=ax.transAxes, zorder=15)
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3, linestyle="--", linewidth=0.5)
    ax.legend(loc="center left", framealpha=0.95, fontsize=11, bbox_to_anchor=(1.02, 0.5))
    
    # Add text box
    textstr = (
        "STATE SPACE:\n"
        f"Total nodes: {len(intersections)}\n"
        f"Camera zones: {len(cameras)}\n"
        "Problem space: 40th-61st, Lex-8th/CPW\n"
        "Extended corridor for Pareto\n"
        "\n"
        "Voronoi assigns features:\n"
        "Each intersection inherits\n"
        "features from nearest camera"
    )
    ax.text(
        0.02,
        0.98,
        textstr,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.9, edgecolor="black", linewidth=1.5),
    )
    
    plt.tight_layout()
    plt.savefig(output, dpi=300, bbox_inches="tight")
    plt.close()
    LOGGER.info("Saved map to %s", output)


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--intersections",
        type=Path,
        default=Path("data/actual_intersections.json"),
        help="Path to intersection data JSON",
    )
    parser.add_argument(
        "--cameras",
        type=Path,
        default=Path("data/corridor_88_cameras.json"),
        help="Path to camera data JSON (or use --fetch-api to get from API)",
    )
    parser.add_argument(
        "--fetch-api",
        action="store_true",
        help="Fetch cameras from NYCTMC API instead of using file",
    )
    parser.add_argument(
        "--streets",
        type=Path,
        default=Path("docs/data/dcm/DCM_StreetCenterLine.shp"),
        help="Path to DCM street centerline shapefile",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/voronoi_tessellation_final.png"),
        help="Output path for the map",
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
    
    # Load or fetch cameras - try API first, fall back to file
    LOGGER.info("Fetching cameras from NYCTMC API...")
    cameras = fetch_all_cameras_from_api()
    if not cameras:
        LOGGER.warning("Failed to fetch cameras from API. Falling back to file: %s", args.cameras)
        cameras = load_cameras(args.cameras)
    LOGGER.info("Loaded %d cameras", len(cameras))
    
    LOGGER.info("Loading streets from %s", args.streets)
    streets = load_streets(args.streets)
    LOGGER.info("Loaded %d street segments", len(streets))
    
    # Find problem space corridor corners from shapefile geometric intersections
    LOGGER.info("Finding problem space corridor corners from shapefile geometric intersections...")
    corners = find_corridor_corners_from_shapefile(streets)
    LOGGER.info("Found problem space corners: %s", list(corners.keys()))
    
    # Find camera corridor corners
    LOGGER.info("Finding camera corridor corners from shapefile geometric intersections...")
    camera_corridor_corners = find_camera_corridor_corners_from_shapefile(streets)
    LOGGER.info("Found camera corridor corners: %s", list(camera_corridor_corners.keys()))
    
    # Filter cameras to those in purple corridor
    cameras_in_corridor = []
    if camera_corridor_corners and len(camera_corridor_corners) == 4:
        cameras_in_corridor = filter_cameras_in_purple_corridor(cameras, camera_corridor_corners)
        LOGGER.info("Found %d cameras within purple corridor bounds (from %d total)", len(cameras_in_corridor), len(cameras))
    else:
        LOGGER.warning("Camera corridor corners not found, using all cameras")
        cameras_in_corridor = cameras
    
    # Use ALL numbered cameras (those in purple corridor) for Voronoi tessellation
    cameras_for_voronoi = cameras_in_corridor
    
    # Draw map - pass all cameras for plotting (will be filtered/colored in draw function)
    bounds = (40.744, 40.773, -74.003, -73.967)
    draw_corridor_border(corners, cameras, cameras_for_voronoi, intersections, streets, args.output, bounds, camera_corridor_corners)
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

