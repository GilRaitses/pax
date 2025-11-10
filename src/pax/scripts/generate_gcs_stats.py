#!/usr/bin/env python3
"""Generate collection statistics from GCS for the dashboard.

This script queries GCS bucket and generates a stats.json file that can be
served statically for GitHub Pages.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path

from google.cloud import storage

from ..config import PaxSettings

LOGGER = logging.getLogger(__name__)


def parse_timestamp_from_path(blob_name: str) -> datetime | None:
    """Extract timestamp from blob path like: images/camera-id/YYYYMMDDTHHMMSS.jpg
    Assumes timestamps are in Eastern time (America/New_York).
    """
    try:
        parts = blob_name.split("/")
        if len(parts) >= 3:
            filename = parts[-1]
            timestamp_str = filename.replace(".jpg", "").replace(".jpeg", "")
            # Parse as naive datetime, then assume Eastern time
            naive_dt = datetime.strptime(timestamp_str, "%Y%m%dT%H%M%S")
            et_tz = ZoneInfo("America/New_York")
            return naive_dt.replace(tzinfo=et_tz)
    except Exception:
        pass
    return None


def generate_gcs_stats(
    bucket_name: str,
    prefix: str = "images",
    manifest_path: Path | None = None,
) -> dict:
    """Generate statistics from GCS bucket."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    
    LOGGER.info("Listing blobs in gs://%s/%s", bucket_name, prefix)
    blobs = list(bucket.list_blobs(prefix=prefix))
    LOGGER.info("Found %d total blobs", len(blobs))
    
    # Load numbered manifest if available
    camera_manifest = {}
    if manifest_path and manifest_path.exists():
        with open(manifest_path) as f:
            manifest_data = json.load(f)
            for cam in manifest_data.get("cameras", []):
                camera_manifest[cam["id"]] = {
                    "number": cam.get("number"),
                    "name": cam.get("name", ""),
                    "latitude": cam.get("latitude"),
                    "longitude": cam.get("longitude"),
                }
        LOGGER.info("Loaded %d cameras from manifest", len(camera_manifest))
    
    # Process images
    camera_counts: dict[str, dict] = {}
    total_images = 0
    latest_capture = None
    latest_camera_id = None
    latest_image_path = None
    images_by_date: dict[str, int] = defaultdict(int)
    
    for blob in blobs:
        if not blob.name.endswith((".jpg", ".jpeg")):
            continue
        
        total_images += 1
        
        # Extract camera ID and timestamp
        parts = blob.name.split("/")
        if len(parts) >= 3:
            camera_id = parts[-2]
            timestamp = parse_timestamp_from_path(blob.name)
            
            if timestamp:
                # Use Eastern time for date grouping
                timestamp_et = timestamp.astimezone(ZoneInfo("America/New_York")) if timestamp.tzinfo else timestamp.replace(tzinfo=ZoneInfo("America/New_York"))
                date_str = timestamp_et.strftime("%Y-%m-%d")
                images_by_date[date_str] += 1
                
                if camera_id not in camera_counts:
                    camera_counts[camera_id] = {
                        "count": 0,
                        "lastCapture": None,
                        "firstCapture": None,
                    }
                
                camera_counts[camera_id]["count"] += 1
                
                capture_str = timestamp_et.isoformat()
                if not camera_counts[camera_id]["lastCapture"] or capture_str > camera_counts[camera_id]["lastCapture"]:
                    camera_counts[camera_id]["lastCapture"] = capture_str
                
                if not camera_counts[camera_id]["firstCapture"] or capture_str < camera_counts[camera_id]["firstCapture"]:
                    camera_counts[camera_id]["firstCapture"] = capture_str
                
                # Track latest overall
                if not latest_capture or capture_str > latest_capture:
                    latest_capture = capture_str
                    latest_camera_id = camera_id
                    latest_image_path = blob.name
    
    # Get camera names from manifest
    active_cameras = len(camera_manifest) if camera_manifest else len(camera_counts)
    latest_camera_name = None
    if latest_camera_id and camera_manifest.get(latest_camera_id):
        latest_camera_name = camera_manifest[latest_camera_id]["name"]
    
    # Calculate collection period
    sorted_dates = sorted(images_by_date.keys())
    collection_start = sorted_dates[0] if sorted_dates else None
    collection_end = sorted_dates[-1] if sorted_dates else None
    
    # Calculate today's images (Eastern time)
    today = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    today_images = images_by_date.get(today, 0)
    
    # Calculate expected vs actual
    expected_per_day = 82 * 48  # 82 cameras × 48 images/day
    days_active = len(sorted_dates) if sorted_dates else 0
    
    # Construct public URL for latest image
    latest_image_url = None
    if latest_image_path:
        # GCS public URL format: https://storage.googleapis.com/BUCKET_NAME/PATH
        latest_image_url = f"https://storage.googleapis.com/{bucket_name}/{latest_image_path}"
    
    stats = {
        "totalImages": total_images,
        "activeCameras": active_cameras,
        "camerasInManifest": len(camera_manifest),
        "latestCapture": latest_capture,
        "latestCameraId": latest_camera_id,
        "latestCameraName": latest_camera_name,
        "latestImagePath": latest_image_path,
        "latestImageUrl": latest_image_url,
        "cameraCounts": camera_counts,
        "collectionPeriod": {
            "start": collection_start,
            "end": collection_end,
            "days": days_active,
        },
        "imagesByDate": dict(sorted(images_by_date.items())),
        "todayImages": today_images,
        "expectedPerDay": expected_per_day,
        "collectionRate": "48 images per camera per day (every 30 minutes)",
        "storageInfo": f"{total_images:,} images across {len(camera_counts)} cameras",
        "bucket": bucket_name,
        "generatedAt": datetime.now(ZoneInfo("America/New_York")).isoformat(),
    }
    
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bucket",
        help="GCS bucket name (default: from settings)",
    )
    parser.add_argument(
        "--prefix",
        default="images",
        help="GCS prefix (default: images)",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Path to numbered camera manifest (default: data/manifests/corridor_cameras_numbered.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/stats.json"),
        help="Output stats JSON file",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level",
    )
    
    args = parser.parse_args(argv)
    logging.basicConfig(level=args.log_level.upper(), format="%(levelname)s: %(message)s")
    
    settings = PaxSettings()
    bucket_name = args.bucket or settings.remote.bucket or "pax-nyc-images"
    
    manifest_path = args.manifest or Path("data/manifests/corridor_cameras_numbered.json")
    
    try:
        stats = generate_gcs_stats(
            bucket_name=bucket_name,
            prefix=args.prefix,
            manifest_path=manifest_path if manifest_path.exists() else None,
        )
        
        # Write stats
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w") as f:
            json.dump(stats, f, indent=2)
        
        LOGGER.info("Generated stats: %s", args.output)
        LOGGER.info("Total images: %d", stats["totalImages"])
        LOGGER.info("Active cameras: %d", stats["activeCameras"])
        LOGGER.info("Collection period: %s to %s", stats["collectionPeriod"]["start"], stats["collectionPeriod"]["end"])
        
        return 0
        
    except Exception as e:
        LOGGER.exception("Failed to generate stats: %s", e)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

