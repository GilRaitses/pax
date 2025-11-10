#!/usr/bin/env python3
"""Check GCS bucket status - list images, size, and statistics."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from google.cloud import storage

from ..config import PaxSettings

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bucket",
        help="GCS bucket name (default: from settings or PAX_REMOTE_BUCKET)",
    )
    parser.add_argument(
        "--prefix",
        help="GCS prefix/folder (default: from settings or 'images')",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
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


def check_bucket_status(bucket_name: str, prefix: str = "images") -> dict:
    """Check GCS bucket status and return statistics."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    
    LOGGER.info("Listing blobs in gs://%s/%s", bucket_name, prefix)
    
    blobs = list(bucket.list_blobs(prefix=prefix))
    LOGGER.info("Found %d total blobs", len(blobs))
    
    # Statistics
    total_images = 0
    total_size_bytes = 0
    camera_counts: dict[str, int] = defaultdict(int)
    camera_sizes: dict[str, int] = defaultdict(int)
    date_counts: dict[str, int] = defaultdict(int)
    camera_dates: dict[str, set[str]] = defaultdict(set)
    
    # Track file types
    file_types: dict[str, int] = defaultdict(int)
    
    for blob in blobs:
        # Count by file type
        if "." in blob.name:
            ext = blob.name.split(".")[-1].lower()
            file_types[ext] += 1
        
        # Only process images
        if not blob.name.endswith((".jpg", ".jpeg", ".png")):
            continue
        
        total_images += 1
        total_size_bytes += blob.size or 0
        
        # Extract camera ID from path: images/camera-id/timestamp.jpg
        parts = blob.name.split("/")
        if len(parts) >= 3:
            camera_id = parts[-2]
            camera_counts[camera_id] += 1
            camera_sizes[camera_id] += blob.size or 0
            
            # Extract date from timestamp
            timestamp = parse_timestamp_from_path(blob.name)
            if timestamp:
                date_str = timestamp.strftime("%Y-%m-%d")
                date_counts[date_str] += 1
                camera_dates[camera_id].add(date_str)
    
    # Calculate date range
    sorted_dates = sorted(date_counts.keys())
    date_range = {
        "earliest": sorted_dates[0] if sorted_dates else None,
        "latest": sorted_dates[-1] if sorted_dates else None,
        "total_days": len(sorted_dates),
    }
    
    # Per-camera stats
    camera_stats = {}
    for camera_id in camera_counts:
        camera_stats[camera_id] = {
            "image_count": camera_counts[camera_id],
            "size_bytes": camera_sizes[camera_id],
            "size_mb": round(camera_sizes[camera_id] / (1024 * 1024), 2),
            "dates_collected": sorted(camera_dates[camera_id]),
            "days_active": len(camera_dates[camera_id]),
        }
    
    status = {
        "bucket": bucket_name,
        "prefix": prefix,
        "summary": {
            "total_blobs": len(blobs),
            "total_images": total_images,
            "total_size_bytes": total_size_bytes,
            "total_size_mb": round(total_size_bytes / (1024 * 1024), 2),
            "total_size_gb": round(total_size_bytes / (1024 * 1024 * 1024), 2),
            "unique_cameras": len(camera_counts),
            "file_types": dict(file_types),
        },
        "date_range": date_range,
        "images_by_date": dict(sorted(date_counts.items())),
        "cameras": camera_stats,
        "checked_at": datetime.now().isoformat(),
    }
    
    return status


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    
    logging.basicConfig(level=args.log_level.upper(), format="%(levelname)s: %(message)s")
    
    # Load settings
    settings = PaxSettings()
    bucket_name = args.bucket or settings.remote.bucket or None
    prefix = args.prefix or settings.remote.prefix or "images"
    
    if not bucket_name:
        LOGGER.error("No bucket specified. Use --bucket or configure PAX_REMOTE_BUCKET")
        LOGGER.info("Common bucket names: pax-nyc-images")
        return 1
    
    try:
        status = check_bucket_status(bucket_name, prefix)
        
        if args.json:
            print(json.dumps(status, indent=2))
        else:
            # Pretty print
            print("\n" + "=" * 70)
            print(f"GCS Bucket Status: gs://{status['bucket']}/{status['prefix']}")
            print("=" * 70)
            print(f"\nSummary:")
            print(f"  Total blobs: {status['summary']['total_blobs']:,}")
            print(f"  Total images: {status['summary']['total_images']:,}")
            print(f"  Total size: {status['summary']['total_size_mb']:.2f} MB ({status['summary']['total_size_gb']:.2f} GB)")
            print(f"  Unique cameras: {status['summary']['unique_cameras']}")
            
            if status['summary']['file_types']:
                print(f"\nFile types:")
                for ext, count in sorted(status['summary']['file_types'].items()):
                    print(f"  .{ext}: {count:,}")
            
            if status['date_range']['earliest']:
                print(f"\nCollection Period:")
                print(f"  Earliest: {status['date_range']['earliest']}")
                print(f"  Latest: {status['date_range']['latest']}")
                print(f"  Total days: {status['date_range']['total_days']}")
            
            if status['images_by_date']:
                print(f"\nImages by Date (last 10 days):")
                for date, count in list(sorted(status['images_by_date'].items()))[-10:]:
                    print(f"  {date}: {count:,} images")
            
            if status['cameras']:
                print(f"\nTop 10 Cameras by Image Count:")
                sorted_cameras = sorted(
                    status['cameras'].items(),
                    key=lambda x: x[1]['image_count'],
                    reverse=True
                )
                for camera_id, stats in sorted_cameras[:10]:
                    print(f"  {camera_id}: {stats['image_count']:,} images, {stats['size_mb']:.2f} MB, {stats['days_active']} days")
            
            print(f"\nChecked at: {status['checked_at']}")
            print("=" * 70 + "\n")
        
        return 0
        
    except Exception as e:
        LOGGER.exception("Failed to check bucket status: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())

