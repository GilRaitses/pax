"""Fetch all cameras in expanded corridor (34th-66th St, Lexington to 8th Ave) and generate Voronoi zones."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import yaml

from ..config import PaxSettings
from ..data_collection.camera_client import CameraAPIClient

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-manifest",
        type=Path,
        default=Path("cameras_expanded_34th_66th.yaml"),
        help="Output manifest file (default: cameras_expanded_34th_66th.yaml)",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("data/voronoi_zones/cameras_expanded_34th_66th.json"),
        help="Output JSON file (default: data/voronoi_zones/cameras_expanded_34th_66th.json)",
    )
    parser.add_argument(
        "--lat-min",
        type=float,
        default=40.748,  # ~34th St
        help="Minimum latitude (default: 40.748 for 34th St)",
    )
    parser.add_argument(
        "--lat-max",
        type=float,
        default=40.773,  # ~66th St
        help="Maximum latitude (default: 40.773 for 66th St)",
    )
    parser.add_argument(
        "--lon-min",
        type=float,
        default=-73.998,  # Approx. 9th Avenue west boundary
        help="Minimum longitude (west boundary, default: -73.998 for ~9th Ave)",
    )
    parser.add_argument(
        "--lon-max",
        type=float,
        default=-73.970,  # Approx. 3rd Avenue east boundary
        help="Maximum longitude (east boundary, default: -73.970 for ~3rd Ave)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level",
    )
    return parser


def filter_cameras_in_corridor(
    all_cameras: list[dict],
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
) -> list[dict]:
    """Filter cameras to corridor bounds."""
    corridor_cameras = []
    
    for cam in all_cameras:
        try:
            lat = float(cam.get("latitude", 0))
            lon = float(cam.get("longitude", 0))
            area = cam.get("area", "")
            
            if (area == "Manhattan" and
                lat_min <= lat <= lat_max and
                lon_min <= lon <= lon_max):
                corridor_cameras.append(cam)
        except (ValueError, TypeError):
            LOGGER.debug("Skipping camera with invalid coordinates: %s", cam.get("id"))
            continue
    
    return corridor_cameras


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    
    logging.basicConfig(level=args.log_level.upper(), format="%(levelname)s: %(message)s")
    
    # Fetch all cameras from API
    LOGGER.info("Fetching all cameras from NYCTMC API...")
    client = CameraAPIClient(PaxSettings())
    all_cameras = client.list_cameras()
    
    LOGGER.info("Found %d total cameras", len(all_cameras))
    
    # Filter to corridor
    corridor_cameras = filter_cameras_in_corridor(
        all_cameras,
        args.lat_min,
        args.lat_max,
        args.lon_min,
        args.lon_max,
    )
    
    LOGGER.info("Found %d cameras in corridor (34th-66th St, Lexington to 8th Ave)", len(corridor_cameras))
    
    # Create manifest structure
    manifest = {
        "project": {
            "name": "Pax NYC - Expanded Corridor (34th-66th St)",
            "description": "All cameras in expanded corridor for Voronoi zone generation",
            "study_area": {
                "start": "34th Street area",
                "goal": "66th Street area",
                "bounds": f"{args.lat_min:.4f}-{args.lat_max:.4f} Streets, {args.lon_min:.4f} to {args.lon_max:.4f} Longitude",
            },
        },
        "schedule": {
            "interval_minutes": 30,
            "active_hours": {
                "start": "06:00",
                "end": "22:00",
            },
            "timezone": "America/New_York",
        },
        "cameras": [],
    }
    
    # Add cameras to manifest
    for cam in corridor_cameras:
        manifest["cameras"].append({
            "id": cam["id"],
            "name": cam.get("name", ""),
            "area": cam.get("area", "Manhattan"),
            "latitude": float(cam.get("latitude", 0)),
            "longitude": float(cam.get("longitude", 0)),
            "priority": "medium",
        })
    
    # Sort by latitude (south to north)
    manifest["cameras"].sort(key=lambda c: c["latitude"])
    
    # Save YAML manifest
    args.output_manifest.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_manifest, "w") as f:
        yaml.dump(manifest, f, default_flow_style=False, sort_keys=False, allow_unicode=True, indent=2)
    
    LOGGER.info("Saved manifest to %s", args.output_manifest)
    
    # Save JSON for easy inspection
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_json, "w") as f:
        json.dump(corridor_cameras, f, indent=2)
    
    LOGGER.info("Saved JSON to %s", args.output_json)
    
    print("\n" + "=" * 70)
    print("EXPANDED CORRIDOR CAMERAS FETCHED")
    print("=" * 70)
    print(f"\nTotal cameras in corridor: {len(corridor_cameras)}")
    print(f"Bounds: {args.lat_min:.4f}-{args.lat_max:.4f} lat, {args.lon_min:.4f}-{args.lon_max:.4f} lon")
    print(f"\nManifest: {args.output_manifest}")
    print(f"JSON: {args.output_json}")
    print(f"\nNext step: Generate Voronoi zones with:")
    print(f"  python -m pax.scripts.generate_voronoi_zones \\")
    print(f"    --manifest {args.output_manifest} \\")
    print(f"    --output-dir data/voronoi_zones/expanded_34th_66th \\")
    print(f"    --dcm-shapefile 'docs/term project/DCM_StreetCenterLine.shp' \\")
    print(f"    --clip-to-streets")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

