#!/usr/bin/env python3
"""Identify zones with sufficient data for baseline generation.

Lists zones by data completeness:
- Zones with ≥3 images (sufficient for baseline)
- Zones with 1-2 images (partial data)
- Zones with 0 images (missing data)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml


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
        }

    return camera_images


def identify_zones_sufficient_data(
    camera_manifest_path: Path,
    image_manifest_path: Path,
    output_path: Path | None = None,
) -> dict:
    """Identify zones with sufficient data and generate completeness report."""
    print("Loading camera manifest...")
    camera_map = load_camera_manifest(camera_manifest_path)
    print(f"Loaded {len(camera_map)} cameras")

    print("Loading image manifest...")
    image_data = load_image_manifest(image_manifest_path)
    print(f"Loaded image data for {len(image_data)} cameras")

    # Group by zone (camera number)
    zone_data = {}
    for camera_id, camera_info in camera_map.items():
        camera_number = camera_info["number"]
        image_count = image_data.get(camera_id, {}).get("total_images", 0)

        if camera_number not in zone_data:
            zone_data[camera_number] = {
                "zone_number": camera_number,
                "cameras": [],
                "total_images": 0,
            }

        zone_data[camera_number]["cameras"].append(
            {
                "camera_id": camera_id,
                "camera_name": camera_info["name"],
                "image_count": image_count,
            }
        )
        zone_data[camera_number]["total_images"] += image_count

    # Categorize zones
    zones_sufficient = []  # ≥3 images
    zones_partial = []  # 1-2 images
    zones_missing = []  # 0 images

    for zone_number in sorted(zone_data.keys()):
        zone_info = zone_data[zone_number]
        total_images = zone_info["total_images"]

        zone_entry = {
            "zone_number": zone_number,
            "total_images": total_images,
            "camera_count": len(zone_info["cameras"]),
            "cameras": zone_info["cameras"],
        }

        if total_images >= 3:
            zones_sufficient.append(zone_entry)
        elif total_images >= 1:
            zones_partial.append(zone_entry)
        else:
            zones_missing.append(zone_entry)

    # Generate report
    report = {
        "metadata": {
            "total_zones": len(zone_data),
            "zones_sufficient": len(zones_sufficient),
            "zones_partial": len(zones_partial),
            "zones_missing": len(zones_missing),
            "sufficient_threshold": 3,
            "total_images": sum(zone["total_images"] for zone in zone_data.values()),
        },
        "zones_sufficient": zones_sufficient,
        "zones_partial": zones_partial,
        "zones_missing": zones_missing,
        "summary": {
            "sufficient_percentage": (len(zones_sufficient) / len(zone_data) * 100) if zone_data else 0,
            "partial_percentage": (len(zones_partial) / len(zone_data) * 100) if zone_data else 0,
            "missing_percentage": (len(zones_missing) / len(zone_data) * 100) if zone_data else 0,
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
    print("DATA COMPLETENESS REPORT")
    print("=" * 60)
    print(f"Total zones: {len(zone_data)}")
    print(f"\nZones with sufficient data (≥3 images): {len(zones_sufficient)} ({report['summary']['sufficient_percentage']:.1f}%)")
    print(f"Zones with partial data (1-2 images): {len(zones_partial)} ({report['summary']['partial_percentage']:.1f}%)")
    print(f"Zones with missing data (0 images): {len(zones_missing)} ({report['summary']['missing_percentage']:.1f}%)")
    print(f"\nTotal images: {report['metadata']['total_images']}")

    if zones_sufficient:
        print("\nZones with sufficient data:")
        for zone in zones_sufficient[:10]:
            print(f"  Zone {zone['zone_number']}: {zone['total_images']} images ({zone['camera_count']} cameras)")
        if len(zones_sufficient) > 10:
            print(f"  ... and {len(zones_sufficient) - 10} more")

    if zones_partial:
        print("\nZones with partial data:")
        for zone in zones_partial[:10]:
            print(f"  Zone {zone['zone_number']}: {zone['total_images']} images ({zone['camera_count']} cameras)")
        if len(zones_partial) > 10:
            print(f"  ... and {len(zones_partial) - 10} more")

    if zones_missing:
        print("\nZones with missing data:")
        for zone in zones_missing[:10]:
            print(f"  Zone {zone['zone_number']}: {zone['camera_count']} cameras, 0 images")
        if len(zones_missing) > 10:
            print(f"  ... and {len(zones_missing) - 10} more")

    return report


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Identify zones with sufficient data")
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
        default=Path("docs/reports/data_completeness.json"),
        help="Output path for report (default: docs/reports/data_completeness.json)",
    )

    args = parser.parse_args()

    if not args.camera_manifest.exists():
        print(f"ERROR: Camera manifest not found: {args.camera_manifest}")
        sys.exit(1)

    if not args.image_manifest.exists():
        print(f"ERROR: Image manifest not found: {args.image_manifest}")
        sys.exit(1)

    identify_zones_sufficient_data(args.camera_manifest, args.image_manifest, args.output)


if __name__ == "__main__":
    main()

