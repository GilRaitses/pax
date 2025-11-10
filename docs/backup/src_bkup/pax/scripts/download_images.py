"""Download all collected images from GCS and organize by day with manifest."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml
from google.cloud import storage

from ..config import PaxSettings

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bucket",
        help="GCS bucket name (default: from settings)",
    )
    parser.add_argument(
        "--prefix",
        help="GCS prefix/folder (default: from settings)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/downloaded_images"),
        help="Output directory for downloaded images (default: data/downloaded_images)",
    )
    parser.add_argument(
        "--manifest-path",
        type=Path,
        default=Path("data/image_manifest.yaml"),
        help="Path to save manifest YAML (default: data/image_manifest.yaml)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files without downloading",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level",
    )
    return parser


def parse_timestamp_from_path(blob_name: str) -> datetime | None:
    """Extract timestamp from blob path like: images/camera-id/YYYYMMDDTHHMMSS.jpg"""
    try:
        parts = blob_name.split("/")
        if len(parts) >= 3:
            filename = parts[-1]
            timestamp_str = filename.replace(".jpg", "").replace(".jpeg", "")
            return datetime.strptime(timestamp_str, "%Y%m%dT%H%M%S")
    except Exception:
        pass
    return None


def download_images(
    bucket_name: str,
    prefix: str,
    output_dir: Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Download images from GCS and organize by day."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    
    # Track all images
    camera_images: dict[str, list[dict[str, Any]]] = defaultdict(list)
    total_images = 0
    downloaded = 0
    
    LOGGER.info("Listing blobs in gs://%s/%s", bucket_name, prefix)
    
    blobs = list(bucket.list_blobs(prefix=prefix))
    LOGGER.info("Found %d blobs", len(blobs))
    
    for blob in blobs:
        if not blob.name.endswith((".jpg", ".jpeg")):
            continue
        
        total_images += 1
        timestamp = parse_timestamp_from_path(blob.name)
        
        if not timestamp:
            LOGGER.warning("Could not parse timestamp from %s", blob.name)
            continue
        
        # Extract camera ID from path: images/camera-id/timestamp.jpg
        parts = blob.name.split("/")
        if len(parts) < 3:
            continue
        
        camera_id = parts[-2]
        date_str = timestamp.strftime("%Y-%m-%d")
        
        # Create day directory
        day_dir = output_dir / date_str
        if not dry_run:
            day_dir.mkdir(parents=True, exist_ok=True)
        
        # Download path
        local_path = day_dir / f"{camera_id}_{timestamp.strftime('%Y%m%dT%H%M%S')}.jpg"
        
        image_info = {
            "camera_id": camera_id,
            "timestamp": timestamp.isoformat(),
            "date": date_str,
            "gcs_path": blob.name,
            "local_path": str(local_path.relative_to(output_dir.parent)) if not dry_run else None,
            "size_bytes": blob.size,
        }
        
        camera_images[camera_id].append(image_info)
        
        if not dry_run:
            LOGGER.info("Downloading %s -> %s", blob.name, local_path)
            blob.download_to_filename(local_path)
            downloaded += 1
        else:
            LOGGER.info("Would download %s -> %s", blob.name, local_path)
    
    # Sort images by timestamp for each camera
    for camera_id in camera_images:
        camera_images[camera_id].sort(key=lambda x: x["timestamp"])
    
    LOGGER.info("Processed %d images (%d downloaded)", total_images, downloaded)
    
    return {
        "camera_images": dict(camera_images),
        "total_images": total_images,
        "downloaded": downloaded,
    }


def create_manifest(
    camera_images: dict[str, list[dict[str, Any]]],
    output_path: Path,
    bucket_name: str,
) -> None:
    """Create manifest YAML with camera stats and time ranges."""
    
    # Calculate stats per camera
    cameras: dict[str, dict[str, Any]] = {}
    all_dates = set()
    
    for camera_id, images in camera_images.items():
        if not images:
            continue
        
        timestamps = [datetime.fromisoformat(img["timestamp"]) for img in images]
        earliest = min(timestamps)
        latest = max(timestamps)
        date_range = (latest - earliest).total_seconds() / 3600  # hours
        
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
                "duration_hours": round(date_range, 2),
                "duration_days": round(date_range / 24, 2),
            },
            "images_by_date": dict(sorted(images_by_date.items())),
            "images": [
                {
                    "timestamp": img["timestamp"],
                    "date": img["date"],
                    "local_path": img.get("local_path"),
                    "gcs_path": img["gcs_path"],
                    "size_bytes": img["size_bytes"],
                }
                for img in images
            ],
        }
    
    # Calculate collection stats
    sorted_dates = sorted(all_dates)
    collection_start = sorted_dates[0] if sorted_dates else None
    collection_end = sorted_dates[-1] if sorted_dates else None
    
    # Calculate percentage complete (assuming 30-min intervals over collection period)
    # This is a rough estimate - you may want to adjust based on your requirements
    completion_stats = {}
    if collection_start and collection_end:
        start_dt = datetime.fromisoformat(collection_start)
        end_dt = datetime.fromisoformat(collection_end)
        total_hours = (end_dt - start_dt).total_seconds() / 3600 + 24  # include last day
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
            "bucket": bucket_name,
            "collection_period": {
                "start_date": collection_start,
                "end_date": collection_end,
                "total_days": len(all_dates),
            },
            "total_cameras": len(cameras),
            "total_images": sum(cam["total_images"] for cam in cameras.values()),
            "generated_at": datetime.now().isoformat(),
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
        yaml.dump(manifest, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    
    LOGGER.info("Manifest written to %s", output_path)
    LOGGER.info("Summary: %d cameras, %d total images", len(cameras), manifest["metadata"]["total_images"])


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    
    logging.basicConfig(level=args.log_level.upper(), format="%(levelname)s: %(message)s")
    
    # Load settings
    settings = PaxSettings()
    bucket_name = args.bucket or settings.remote.bucket
    prefix = args.prefix or settings.remote.prefix or "images"
    
    if not bucket_name:
        LOGGER.error("No bucket specified. Use --bucket or configure PAX_REMOTE_BUCKET")
        return 1
    
    # Download images
    LOGGER.info("Downloading images from gs://%s/%s", bucket_name, prefix)
    result = download_images(
        bucket_name=bucket_name,
        prefix=prefix,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
    )
    
    if args.dry_run:
        print(f"\nDry run complete. Would download {result['total_images']} images.")
        return 0
    
    # Create manifest
    LOGGER.info("Creating manifest...")
    create_manifest(
        camera_images=result["camera_images"],
        output_path=args.manifest_path,
        bucket_name=bucket_name,
    )
    
    print(f"\nDownload complete!")
    print(f"  Images downloaded: {result['downloaded']}")
    print(f"  Output directory: {args.output_dir}")
    print(f"  Manifest: {args.manifest_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())



