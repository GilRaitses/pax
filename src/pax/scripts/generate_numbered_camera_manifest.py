#!/usr/bin/env python3
"""Generate numbered camera manifest matching the master partitioning map.

This script filters cameras to the purple corridor (34th-66th St, 3rd-9th/Amsterdam)
and numbers them in the same order as the partitioning map visualization.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point, Polygon

from ..config import PaxSettings

LOGGER = logging.getLogger(__name__)


def fetch_all_cameras_from_api() -> list[dict]:
    """Fetch all online cameras from the NYCTMC API."""
    try:
        from ..data_collection.camera_client import CameraAPIClient
        
        settings = PaxSettings()
        client = CameraAPIClient(settings)
        cameras = client.list_cameras()
        LOGGER.info("Fetched %d cameras from API", len(cameras))
        return cameras
    except Exception as e:
        LOGGER.warning("Failed to fetch cameras from CameraAPIClient: %s", e)
        # Fallback to direct requests
        try:
            import requests
            api_url = "https://webcams.nyctmc.org/api/cameras"
            response = requests.get(api_url, timeout=30)
            response.raise_for_status()
            all_cameras = response.json()
            cameras = [cam for cam in all_cameras if cam.get("isOnline") == "true"]
            LOGGER.info("Fetched %d online cameras from API directly", len(cameras))
            return cameras
        except Exception as e2:
            LOGGER.error("Failed to fetch cameras from API: %s", e2)
            return []


def find_camera_corridor_corners_from_shapefile(streets: gpd.GeoDataFrame) -> dict[str, tuple[float, float]]:
    """Find camera corridor corners: 34th-66th St, 3rd-9th/Amsterdam."""
    # Camera corridor: 34th-66th St, 3rd-9th/Amsterdam (above 59th St)
    target_streets = {
        "north": ["66", "66TH", "66 ST", "66 STREET"],
        "south": ["34", "34TH", "34 ST", "34 STREET"],
        "west": ["9", "9TH", "9 AVE", "9 AVENUE", "AMSTERDAM", "COLUMBUS"],
        "east": ["3", "3RD", "3 AVE", "3 AVENUE", "THIRD"],
    }
    
    corners = {}
    
    # Find intersections
    for idx1, street1 in streets.iterrows():
        name1 = str(street1.get("FULL_STREE", "")).upper()
        geom1 = street1.geometry
        
        for idx2, street2 in streets.iterrows():
            if idx1 >= idx2:
                continue
            
            name2 = str(street2.get("FULL_STREE", "")).upper()
            geom2 = street2.geometry
            
            # Check for NW corner: 66th & 9th/Amsterdam/Columbus
            if any(s in name1 for s in target_streets["north"]) and any(s in name2 for s in target_streets["west"]):
                if geom1.intersects(geom2):
                    point = geom1.intersection(geom2)
                    if hasattr(point, 'x') and hasattr(point, 'y'):
                        corners["NW"] = (point.x, point.y)
                        LOGGER.info("Found NW corner: %s x %s at (%.6f, %.6f)", name1, name2, point.x, point.y)
            
            # Check for NE corner: 66th & 3rd
            if any(s in name1 for s in target_streets["north"]) and any(s in name2 for s in target_streets["east"]):
                if geom1.intersects(geom2):
                    point = geom1.intersection(geom2)
                    if hasattr(point, 'x') and hasattr(point, 'y'):
                        corners["NE"] = (point.x, point.y)
                        LOGGER.info("Found NE corner: %s x %s at (%.6f, %.6f)", name1, name2, point.x, point.y)
            
            # Check for SE corner: 34th & 3rd
            if any(s in name1 for s in target_streets["south"]) and any(s in name2 for s in target_streets["east"]):
                if geom1.intersects(geom2):
                    point = geom1.intersection(geom2)
                    if hasattr(point, 'x') and hasattr(point, 'y'):
                        corners["SE"] = (point.x, point.y)
                        LOGGER.info("Found SE corner: %s x %s at (%.6f, %.6f)", name1, name2, point.x, point.y)
            
            # Check for SW corner: 34th & 9th
            if any(s in name1 for s in target_streets["south"]) and any(s in name2 for s in target_streets["west"]):
                if geom1.intersects(geom2):
                    point = geom1.intersection(geom2)
                    if hasattr(point, 'x') and hasattr(point, 'y'):
                        corners["SW"] = (point.x, point.y)
                        LOGGER.info("Found SW corner: %s x %s at (%.6f, %.6f)", name1, name2, point.x, point.y)
    
    if len(corners) != 4:
        LOGGER.warning("Found only %d corners, expected 4", len(corners))
        # Use known coordinates if shapefile lookup fails
        corners = {
            "NW": (-73.981573, 40.773602),  # Columbus/Amsterdam & 66th
            "NE": (-73.963402, 40.765911),  # 3rd Ave & 66th
            "SE": (-73.978124, 40.745727),  # 3rd Ave & 34th
            "SW": (-73.996303, 40.753389),  # 9th Ave & 34th
        }
        LOGGER.info("Using known corner coordinates")
    
    return corners


def filter_cameras_in_purple_corridor(
    cameras: list[dict],
    camera_corridor_corners: dict[str, tuple[float, float]],
) -> list[dict]:
    """Filter cameras that are within the purple camera corridor bounds (including on boundary).
    
    Returns cameras in the same order they appear in the partitioning map.
    """
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
    LOGGER.info("Loading streets from %s", path)
    streets = gpd.read_file(path)
    LOGGER.info("Loaded %d street segments", len(streets))
    return streets


def generate_manifest(
    cameras: list[dict],
    output_path: Path,
    streets_path: Path | None = None,
) -> None:
    """Generate numbered camera manifest matching partitioning map order."""
    
    # If streets path provided, use shapefile to find corners
    camera_corridor_corners = None
    if streets_path and streets_path.exists():
        streets = load_streets(streets_path)
        camera_corridor_corners = find_camera_corridor_corners_from_shapefile(streets)
    else:
        # Use known coordinates
        camera_corridor_corners = {
            "NW": (-73.981573, 40.773602),  # Columbus/Amsterdam & 66th
            "NE": (-73.963402, 40.765911),  # 3rd Ave & 66th
            "SE": (-73.978124, 40.745727),  # 3rd Ave & 34th
            "SW": (-73.996303, 40.753389),  # 9th Ave & 34th
        }
        LOGGER.info("Using known camera corridor corner coordinates")
    
    # Filter cameras to purple corridor (same logic as partitioning map)
    cameras_in_corridor = filter_cameras_in_purple_corridor(cameras, camera_corridor_corners)
    
    # Create numbered manifest (numbers start at 1, matching partitioning map)
    numbered_cameras = []
    for num, cam in enumerate(cameras_in_corridor, start=1):
        numbered_cameras.append({
            "number": num,
            "id": cam.get("id"),
            "name": cam.get("name", ""),
            "latitude": cam.get("latitude"),
            "longitude": cam.get("longitude"),
            "area": cam.get("area", ""),
            "isOnline": cam.get("isOnline", ""),
        })
    
    manifest = {
        "metadata": {
            "total_cameras": len(numbered_cameras),
            "corridor": {
                "boundary": "34th-66th St, 3rd-9th/Amsterdam",
                "corners": camera_corridor_corners,
            },
            "generated_at": __import__("datetime").datetime.now().isoformat(),
        },
        "cameras": numbered_cameras,
    }
    
    # Write JSON
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        json.dump(manifest, f, indent=2)
    
    LOGGER.info("Generated numbered manifest with %d cameras: %s", len(numbered_cameras), output_path)
    
    # Also write YAML for compatibility
    yaml_path = output_path.with_suffix(".yaml")
    try:
        import yaml
        with yaml_path.open("w") as f:
            yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)
        LOGGER.info("Also wrote YAML manifest: %s", yaml_path)
    except ImportError:
        LOGGER.warning("PyYAML not installed, skipping YAML output")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/manifests/corridor_cameras_numbered.json"),
        help="Output manifest path",
    )
    parser.add_argument(
        "--streets",
        type=Path,
        help="Path to street shapefile (optional, uses known coordinates if not provided)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level",
    )
    
    args = parser.parse_args(argv)
    logging.basicConfig(level=args.log_level.upper(), format="%(levelname)s: %(message)s")
    
    # Fetch cameras
    cameras = fetch_all_cameras_from_api()
    if not cameras:
        LOGGER.error("No cameras fetched from API")
        return 1
    
    # Generate manifest
    generate_manifest(cameras, args.output, args.streets)
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

