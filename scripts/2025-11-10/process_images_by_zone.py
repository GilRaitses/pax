#!/usr/bin/env python3
"""Process available images per camera zone.

Groups images by camera zone, counts images per zone, and identifies zones with sufficient data (≥3 images).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def load_camera_manifest(manifest_path: Path) -> dict[str, dict]:
    """Load camera manifest and create mapping from camera_id to camera number."""
    with open(manifest_path) as f:
        manifest = json.load(f)

    camera_map = {}
    for camera in manifest.get("cameras", []):
        camera_id = camera.get("id")
        camera_number = camera.get("number")
        if camera_id and camera_number:
            camera_map[camera_id] = {
                "number": camera_number,
                "name": camera.get("name", ""),
                "latitude": camera.get("latitude"),
                "longitude": camera.get("longitude"),
            }

    return camera_map


def load_image_manifest(manifest_path: Path) -> dict[str, dict]:
    """Load image manifest and extract image counts per camera."""
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)

    camera_images = {}
    for camera_id, camera_data in manifest.get("cameras", {}).items():
        camera_images[camera_id] = {
            "total_images": camera_data.get("total_images", 0),
            "images": camera_data.get("images", []),
            "images_by_date": camera_data.get("images_by_date", {}),
        }

    return camera_images


def process_images_by_zone(
    camera_manifest_path: Path,
    image_manifest_path: Path,
    output_path: Path | None = None,
) -> dict:
    """Process images by camera zone and generate availability report."""
    print("Loading camera manifest...")
    camera_map = load_camera_manifest(camera_manifest_path)
    print(f"Loaded {len(camera_map)} cameras")

    print("Loading image manifest...")
    image_data = load_image_manifest(image_manifest_path)
    print(f"Loaded image data for {len(image_data)} cameras")

    # Group by camera zone (using camera number as zone identifier)
    zone_stats = defaultdict(lambda: {"cameras": [], "total_images": 0, "camera_ids": []})

    # Process each camera
    for camera_id, camera_info in camera_map.items():
        camera_number = camera_info["number"]
        image_count = image_data.get(camera_id, {}).get("total_images", 0)

        zone_stats[camera_number]["cameras"].append(
            {
                "camera_id": camera_id,
                "camera_number": camera_number,
                "name": camera_info["name"],
                "image_count": image_count,
            }
        )
        zone_stats[camera_number]["total_images"] += image_count
        zone_stats[camera_number]["camera_ids"].append(camera_id)

    # Categorize zones
    zones_sufficient = []  # ≥3 images
    zones_partial = []  # 1-2 images
    zones_missing = []  # 0 images

    for zone_number, stats in sorted(zone_stats.items()):
        total_images = stats["total_images"]
        zone_info = {
            "zone_number": zone_number,
            "total_images": total_images,
            "cameras": stats["cameras"],
            "camera_ids": stats["camera_ids"],
        }

        if total_images >= 3:
            zones_sufficient.append(zone_info)
        elif total_images >= 1:
            zones_partial.append(zone_info)
        else:
            zones_missing.append(zone_info)

    # Generate report
    report = {
        "metadata": {
            "total_zones": len(zone_stats),
            "zones_with_sufficient_data": len(zones_sufficient),
            "zones_with_partial_data": len(zones_partial),
            "zones_with_missing_data": len(zones_missing),
            "total_images": sum(image_data.get(cid, {}).get("total_images", 0) for cid in camera_map.keys()),
        },
        "zones_sufficient": zones_sufficient,
        "zones_partial": zones_partial,
        "zones_missing": zones_missing,
        "zone_stats": {
            zone_num: {
                "total_images": stats["total_images"],
                "camera_count": len(stats["cameras"]),
                "camera_ids": stats["camera_ids"],
            }
            for zone_num, stats in sorted(zone_stats.items())
        },
    }

    # Save report
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to: {output_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("ZONE DATA AVAILABILITY SUMMARY")
    print("=" * 60)
    print(f"Total zones: {len(zone_stats)}")
    print(f"Zones with sufficient data (≥3 images): {len(zones_sufficient)}")
    print(f"Zones with partial data (1-2 images): {len(zones_partial)}")
    print(f"Zones with missing data (0 images): {len(zones_missing)}")
    print(f"Total images: {report['metadata']['total_images']}")
    print("\nZones with sufficient data:")
    for zone in zones_sufficient[:10]:  # Show first 10
        print(f"  Zone {zone['zone_number']}: {zone['total_images']} images")
    if len(zones_sufficient) > 10:
        print(f"  ... and {len(zones_sufficient) - 10} more")

    return report


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Process images by camera zone")
    parser.add_argument(
        "--camera-manifest",
        type=Path,
        default=Path("data/manifests/corridor_cameras_numbered.json"),
        help="Path to camera manifest (default: data/manifests/corridor_cameras_numbered.json)",
    )
    parser.add_argument(
        "--image-manifest",
        type=Path,
        default=Path("data/manifests/image_manifest.yaml"),
        help="Path to image manifest (default: data/manifests/image_manifest.yaml)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/reports/zone_data_availability.json"),
        help="Output path for report (default: docs/reports/zone_data_availability.json)",
    )

    args = parser.parse_args()

    if not args.camera_manifest.exists():
        print(f"ERROR: Camera manifest not found: {args.camera_manifest}")
        sys.exit(1)

    if not args.image_manifest.exists():
        print(f"ERROR: Image manifest not found: {args.image_manifest}")
        sys.exit(1)

    process_images_by_zone(args.camera_manifest, args.image_manifest, args.output)


if __name__ == "__main__":
    main()

