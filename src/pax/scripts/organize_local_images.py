"""Organize local images by day and create comprehensive manifest YAML."""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from ..config import PaxSettings

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--images-dir",
        type=Path,
        help="Source images directory (default: from settings)",
    )
    parser.add_argument(
        "--metadata-dir",
        type=Path,
        help="Source metadata directory (default: from settings)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/organized_images"),
        help="Output directory for organized images (default: data/organized_images)",
    )
    parser.add_argument(
        "--manifest-path",
        type=Path,
        default=Path("data/image_manifest.yaml"),
        help="Path to save manifest YAML (default: data/image_manifest.yaml)",
    )
    parser.add_argument(
        "--copy",
        action="store_true",
        help="Copy images instead of moving them",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level",
    )
    return parser


def load_metadata(metadata_dir: Path) -> dict[str, dict[str, Any]]:
    """Load all metadata files, indexed by camera_id -> timestamp -> data."""
    metadata: dict[str, dict[str, Any]] = defaultdict(dict)
    
    if not metadata_dir.exists():
        LOGGER.warning("Metadata directory does not exist: %s", metadata_dir)
        return metadata
    
    for camera_dir in metadata_dir.iterdir():
        if not camera_dir.is_dir() or camera_dir.name.startswith("batch_"):
            continue
        
        camera_id = camera_dir.name
        for meta_file in camera_dir.glob("*.json"):
            try:
                timestamp_str = meta_file.stem  # e.g., "20251103T221820"
                with open(meta_file) as f:
                    data = json.load(f)
                    metadata[camera_id][timestamp_str] = data
            except Exception as e:
                LOGGER.warning("Failed to load %s: %s", meta_file, e)
    
    return metadata


def organize_images(
    images_dir: Path,
    metadata: dict[str, dict[str, Any]],
    output_dir: Path,
    copy: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Organize images by day and camera."""
    camera_images: dict[str, list[dict[str, Any]]] = defaultdict(list)
    total_images = 0
    organized = 0
    
    if not images_dir.exists():
        LOGGER.warning("Images directory does not exist: %s", images_dir)
        return {"camera_images": {}, "total_images": 0, "organized": 0}
    
    # Scan images directory
    for camera_dir in images_dir.iterdir():
        if not camera_dir.is_dir():
            continue
        
        camera_id = camera_dir.name
        camera_metadata = metadata.get(camera_id, {})
        
        for image_file in camera_dir.glob("*.jpg"):
            total_images += 1
            timestamp_str = image_file.stem  # e.g., "20251103T221820"
            
            # Parse timestamp
            try:
                timestamp = datetime.strptime(timestamp_str, "%Y%m%dT%H%M%S")
            except ValueError:
                LOGGER.warning("Could not parse timestamp from %s", image_file.name)
                continue
            
            date_str = timestamp.strftime("%Y-%m-%d")
            
            # Get metadata if available
            meta_data = camera_metadata.get(timestamp_str, {})
            image_url = meta_data.get("image_url", "")
            captured_at = meta_data.get("captured_at", timestamp.isoformat())
            
            # Create day directory
            day_dir = output_dir / date_str
            if not dry_run:
                day_dir.mkdir(parents=True, exist_ok=True)
            
            # Destination path
            dest_path = day_dir / f"{camera_id}_{timestamp_str}.jpg"
            
            image_info = {
                "camera_id": camera_id,
                "timestamp": timestamp.isoformat(),
                "timestamp_str": timestamp_str,
                "date": date_str,
                "source_path": str(image_file),
                "dest_path": str(dest_path),
                "image_url": image_url,
                "captured_at": captured_at,
                "size_bytes": image_file.stat().st_size if image_file.exists() else 0,
            }
            
            camera_images[camera_id].append(image_info)
            
            if not dry_run:
                if copy:
                    LOGGER.info("Copying %s -> %s", image_file, dest_path)
                    shutil.copy2(image_file, dest_path)
                else:
                    LOGGER.info("Moving %s -> %s", image_file, dest_path)
                    shutil.move(str(image_file), dest_path)
                organized += 1
            else:
                action = "copy" if copy else "move"
                LOGGER.info("Would %s %s -> %s", action, image_file, dest_path)
    
    # Sort images by timestamp for each camera
    for camera_id in camera_images:
        camera_images[camera_id].sort(key=lambda x: x["timestamp"])
    
    LOGGER.info("Processed %d images (%d organized)", total_images, organized)
    
    return {
        "camera_images": dict(camera_images),
        "total_images": total_images,
        "organized": organized,
    }


def create_manifest(
    camera_images: dict[str, list[dict[str, Any]]],
    output_path: Path,
    metadata_dir: Path | None = None,
) -> None:
    """Create comprehensive manifest YAML."""
    
    # Calculate stats per camera
    cameras: dict[str, dict[str, Any]] = {}
    all_dates = set()
    
    for camera_id, images in camera_images.items():
        if not images:
            continue
        
        timestamps = [datetime.fromisoformat(img["timestamp"]) for img in images]
        earliest = min(timestamps)
        latest = max(timestamps)
        date_range_hours = (latest - earliest).total_seconds() / 3600
        
        # Count images per day
        images_by_date: dict[str, int] = defaultdict(int)
        for img in images:
            images_by_date[img["date"]] += 1
            all_dates.add(img["date"])
        
        cameras[camera_id] = {
            "camera_id": camera_id,
            "total_images": len(images),
            "time_range": {
                "earliest": earliest.isoformat(),
                "latest": latest.isoformat(),
                "duration_hours": round(date_range_hours, 2),
                "duration_days": round(date_range_hours / 24, 2),
            },
            "images_by_date": dict(sorted(images_by_date.items())),
            "images": [
                {
                    "timestamp": img["timestamp"],
                    "timestamp_str": img["timestamp_str"],
                    "date": img["date"],
                    "local_path": img["dest_path"],
                    "source_path": img.get("source_path"),
                    "image_url": img.get("image_url", ""),
                    "captured_at": img.get("captured_at", img["timestamp"]),
                    "size_bytes": img["size_bytes"],
                }
                for img in images
            ],
        }
    
    # Calculate collection stats
    sorted_dates = sorted(all_dates)
    collection_start = sorted_dates[0] if sorted_dates else None
    collection_end = sorted_dates[-1] if sorted_dates else None
    
    # Calculate percentage complete
    # Assuming 30-min intervals (2 per hour) over collection period
    completion_stats = {}
    if collection_start and collection_end:
        start_dt = datetime.fromisoformat(collection_start)
        end_dt = datetime.fromisoformat(collection_end)
        # Add 1 day to include the end date fully
        total_hours = ((end_dt - start_dt).days + 1) * 24
        expected_images_per_camera = int(total_hours * 2)  # 2 per hour = 30-min intervals
        
        for camera_id, cam_data in cameras.items():
            actual = cam_data["total_images"]
            expected = expected_images_per_camera
            pct_complete = round((actual / expected * 100) if expected > 0 else 0, 2)
            completion_stats[camera_id] = {
                "actual_images": actual,
                "expected_images": expected,
                "percentage_complete": pct_complete,
            }
    
    manifest = {
        "metadata": {
            "collection_period": {
                "start_date": collection_start,
                "end_date": collection_end,
                "total_days": len(all_dates),
            },
            "total_cameras": len(cameras),
            "total_images": sum(cam["total_images"] for cam in cameras.values()),
            "generated_at": datetime.now().isoformat(),
            "note": "Manifest designed for easy visualization with Python scripts",
        },
        "collection_stats": {
            "date_range": {
                "earliest": collection_start,
                "latest": collection_end,
            },
            "dates_collected": sorted_dates,
            "images_per_date": {
                date: sum(
                    cam.get("images_by_date", {}).get(date, 0)
                    for cam in cameras.values()
                )
                for date in sorted_dates
            },
        },
        "cameras": cameras,
        "completion_stats": completion_stats,
    }
    
    # Write YAML
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        yaml.dump(manifest, f, default_flow_style=False, sort_keys=False, allow_unicode=True, indent=2)
    
    LOGGER.info("Manifest written to %s", output_path)
    LOGGER.info("Summary: %d cameras, %d total images", len(cameras), manifest["metadata"]["total_images"])


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    
    logging.basicConfig(level=args.log_level.upper(), format="%(levelname)s: %(message)s")
    
    # Load settings
    settings = PaxSettings()
    images_dir = args.images_dir or settings.storage.images
    metadata_dir = args.metadata_dir or settings.storage.metadata
    
    if not images_dir or not images_dir.exists():
        LOGGER.error("Images directory not found: %s", images_dir)
        return 1
    
    # Load metadata
    LOGGER.info("Loading metadata from %s", metadata_dir)
    metadata = load_metadata(metadata_dir) if metadata_dir else {}
    
    # Organize images
    LOGGER.info("Organizing images from %s", images_dir)
    result = organize_images(
        images_dir=images_dir,
        metadata=metadata,
        output_dir=args.output_dir,
        copy=args.copy,
        dry_run=args.dry_run,
    )
    
    if args.dry_run:
        print(f"\nDry run complete. Would organize {result['total_images']} images.")
        return 0
    
    # Create manifest
    LOGGER.info("Creating manifest...")
    create_manifest(
        camera_images=result["camera_images"],
        output_path=args.manifest_path,
        metadata_dir=metadata_dir,
    )
    
    print(f"\nOrganization complete!")
    print(f"  Images organized: {result['organized']}")
    print(f"  Output directory: {args.output_dir}")
    print(f"  Manifest: {args.manifest_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

