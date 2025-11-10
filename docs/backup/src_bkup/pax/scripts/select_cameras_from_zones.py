"""Helper script to select cameras from expanded corridor and create filtered manifest."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import yaml

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--zones-json",
        type=Path,
        default=Path("data/voronoi_zones/expanded_34th_66th/voronoi_zones.json"),
        help="Voronoi zones JSON file",
    )
    parser.add_argument(
        "--input-manifest",
        type=Path,
        default=Path("cameras_expanded_34th_66th.yaml"),
        help="Input manifest with all cameras",
    )
    parser.add_argument(
        "--output-manifest",
        type=Path,
        default=Path("cameras_selected.yaml"),
        help="Output manifest with selected cameras",
    )
    parser.add_argument(
        "--camera-ids",
        nargs="+",
        help="Camera IDs to keep (space-separated)",
    )
    parser.add_argument(
        "--exclude-ids",
        nargs="+",
        help="Camera IDs to exclude (space-separated)",
    )
    parser.add_argument(
        "--streets",
        nargs="+",
        help="Keep cameras on these streets (e.g., '5 Ave' 'Broadway')",
    )
    parser.add_argument(
        "--min-street",
        type=int,
        help="Minimum street number (e.g., 40 for 40th St)",
    )
    parser.add_argument(
        "--max-street",
        type=int,
        help="Maximum street number (e.g., 59 for 59th St)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    
    # Load input manifest
    with open(args.input_manifest) as f:
        manifest = yaml.safe_load(f)
    
    all_cameras = manifest.get("cameras", [])
    LOGGER.info("Loaded %d cameras from %s", len(all_cameras), args.input_manifest)
    
    # Filter cameras
    selected_cameras = []
    
    for cam in all_cameras:
        cam_id = cam.get("id")
        cam_name = cam.get("name", "").upper()
        
        # Exclude if in exclude list
        if args.exclude_ids and cam_id in args.exclude_ids:
            continue
        
        # Include if in include list
        if args.camera_ids:
            if cam_id not in args.camera_ids:
                continue
        
        # Filter by street names
        if args.streets:
            matches = False
            for street in args.streets:
                if street.upper() in cam_name:
                    matches = True
                    break
            if not matches:
                continue
        
        # Filter by street number range
        if args.min_street or args.max_street:
            # Extract street number from name (look for patterns like "42 St", "42nd", etc.)
            import re
            street_match = re.search(r'(\d+)\s*(ST|STREET|ND|RD|TH)', cam_name)
            if street_match:
                street_num = int(street_match.group(1))
                if args.min_street and street_num < args.min_street:
                    continue
                if args.max_street and street_num > args.max_street:
                    continue
            else:
                # If no street number found and range specified, skip
                if args.min_street or args.max_street:
                    continue
        
        selected_cameras.append(cam)
    
    LOGGER.info("Selected %d cameras", len(selected_cameras))
    
    # Create output manifest
    output_manifest = manifest.copy()
    output_manifest["cameras"] = selected_cameras
    output_manifest["project"]["name"] = "Pax NYC - Selected Cameras"
    output_manifest["project"]["description"] = f"Selected {len(selected_cameras)} cameras from expanded corridor"
    
    # Save output
    args.output_manifest.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_manifest, "w") as f:
        yaml.dump(output_manifest, f, default_flow_style=False, sort_keys=False, allow_unicode=True, indent=2)
    
    print("\n" + "=" * 70)
    print("CAMERAS SELECTED")
    print("=" * 70)
    print(f"\nSelected {len(selected_cameras)} cameras:")
    for i, cam in enumerate(selected_cameras, 1):
        print(f"{i:2d}. {cam['name']}")
    
    print(f"\nSaved to: {args.output_manifest}")
    print(f"\nTo generate Voronoi zones for selected cameras:")
    print(f"  python -m pax.scripts.generate_voronoi_zones \\")
    print(f"    --manifest {args.output_manifest} \\")
    print(f"    --output-dir data/voronoi_zones/selected \\")
    print(f"    --dcm-shapefile 'docs/term project/DCM_StreetCenterLine.shp' \\")
    print(f"    --clip-to-streets")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())


