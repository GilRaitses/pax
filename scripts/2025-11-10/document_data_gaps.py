#!/usr/bin/env python3
"""Document data gaps and create data collection priority list.

Identifies which zones need more images and estimates when full baseline can be generated.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
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
            "images_by_date": camera_data.get("images_by_date", {}),
        }

    return camera_images


def estimate_collection_rate(image_manifest: dict) -> float:
    """Estimate images per day collection rate."""
    metadata = image_manifest.get("metadata", {})
    collection_period = metadata.get("collection_period", {})
    total_days = collection_period.get("total_days", 1)
    total_images = metadata.get("total_images", 0)

    if total_days == 0:
        return 0.0

    return total_images / total_days


def document_data_gaps(
    camera_manifest_path: Path,
    image_manifest_path: Path,
    target_images_per_zone: int = 672,  # 2 weeks * 48 images/day
    output_path: Path | None = None,
) -> dict:
    """Document data gaps and create priority list."""
    print("Loading camera manifest...")
    camera_map = load_camera_manifest(camera_manifest_path)
    print(f"Loaded {len(camera_map)} cameras")

    print("Loading image manifest...")
    with open(image_manifest_path) as f:
        image_manifest = yaml.safe_load(f)
    image_data = load_image_manifest(image_manifest_path)
    print(f"Loaded image data for {len(image_data)} cameras")

    # Estimate collection rate
    collection_rate = estimate_collection_rate(image_manifest)
    print(f"Estimated collection rate: {collection_rate:.1f} images/day")

    # Group by zone
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

    # Analyze gaps
    zones_needing_more = []
    zones_sufficient = []

    for zone_number in sorted(zone_data.keys()):
        zone_info = zone_data[zone_number]
        total_images = zone_info["total_images"]
        images_needed = max(0, target_images_per_zone - total_images)

        zone_entry = {
            "zone_number": zone_number,
            "current_images": total_images,
            "images_needed": images_needed,
            "camera_count": len(zone_info["cameras"]),
            "cameras": zone_info["cameras"],
            "completion_percentage": (total_images / target_images_per_zone * 100) if target_images_per_zone > 0 else 0,
        }

        if images_needed > 0:
            # Estimate days needed (assuming uniform collection rate)
            if collection_rate > 0:
                days_needed = images_needed / collection_rate
                zone_entry["estimated_days_to_complete"] = days_needed
                zone_entry["estimated_completion_date"] = (
                    datetime.now() + timedelta(days=int(days_needed))
                ).isoformat()
            else:
                zone_entry["estimated_days_to_complete"] = None
                zone_entry["estimated_completion_date"] = None

            zones_needing_more.append(zone_entry)
        else:
            zones_sufficient.append(zone_entry)

    # Sort by priority (most images needed first, then by zone number)
    zones_needing_more.sort(key=lambda x: (-x["images_needed"], x["zone_number"]))

    # Create priority list (top 20 zones needing most images)
    priority_list = zones_needing_more[:20]

    # Generate report
    report = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "target_images_per_zone": target_images_per_zone,
            "collection_rate_images_per_day": collection_rate,
            "total_zones": len(zone_data),
            "zones_sufficient": len(zones_sufficient),
            "zones_needing_more": len(zones_needing_more),
        },
        "summary": {
            "total_images_collected": sum(zone["total_images"] for zone in zone_data.values()),
            "total_images_needed": sum(zone["images_needed"] for zone in zones_needing_more),
            "overall_completion_percentage": (
                sum(zone["total_images"] for zone in zone_data.values())
                / (len(zone_data) * target_images_per_zone)
                * 100
            )
            if zone_data
            else 0,
        },
        "priority_list": priority_list,
        "zones_needing_more": zones_needing_more,
        "zones_sufficient": zones_sufficient,
    }

    # Save report
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to: {output_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("DATA GAPS REPORT")
    print("=" * 60)
    print(f"Target images per zone: {target_images_per_zone} (2 weeks = 672 images)")
    print(f"Collection rate: {collection_rate:.1f} images/day")
    print(f"\nTotal zones: {len(zone_data)}")
    print(f"Zones with sufficient data: {len(zones_sufficient)}")
    print(f"Zones needing more images: {len(zones_needing_more)}")
    print(f"\nTotal images collected: {report['summary']['total_images_collected']}")
    print(f"Total images needed: {report['summary']['total_images_needed']}")
    print(f"Overall completion: {report['summary']['overall_completion_percentage']:.1f}%")

    if priority_list:
        print("\nTop priority zones (most images needed):")
        for zone in priority_list[:10]:
            print(f"  Zone {zone['zone_number']}: {zone['current_images']} images, need {zone['images_needed']} more")
            if zone.get("estimated_days_to_complete"):
                print(f"    Estimated completion: {zone['estimated_days_to_complete']:.1f} days")

    # Estimate full baseline completion
    if collection_rate > 0 and zones_needing_more:
        max_images_needed = max(zone["images_needed"] for zone in zones_needing_more)
        max_days_needed = max_images_needed / collection_rate
        print(f"\nEstimated time to full baseline: {max_days_needed:.1f} days")
        print(f"Estimated completion date: {(datetime.now() + timedelta(days=int(max_days_needed))).strftime('%Y-%m-%d')}")

    return report


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Document data gaps and create priority list")
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
        "--target-images",
        type=int,
        default=672,
        help="Target images per zone for full baseline (default: 672 = 2 weeks)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/reports/data_gaps.json"),
        help="Output path for report (default: docs/reports/data_gaps.json)",
    )

    args = parser.parse_args()

    if not args.camera_manifest.exists():
        print(f"ERROR: Camera manifest not found: {args.camera_manifest}")
        sys.exit(1)

    if not args.image_manifest.exists():
        print(f"ERROR: Image manifest not found: {args.image_manifest}")
        sys.exit(1)

    document_data_gaps(args.camera_manifest, args.image_manifest, args.target_images, args.output)


if __name__ == "__main__":
    main()

