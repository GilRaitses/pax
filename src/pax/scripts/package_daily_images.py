#!/usr/bin/env python3
"""Package all images from a 24-hour period (midnight to midnight) into archives.

Creates daily archives organized by date, ready for download.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import tarfile
import zipfile
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from google.cloud import storage

from ..config import PaxSettings

LOGGER = logging.getLogger(__name__)


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


def package_daily_images(
    bucket_name: str,
    prefix: str,
    target_date: str | None = None,
    output_dir: Path | None = None,
    format: str = "zip",
) -> Path:
    """Package all images from a specific date (midnight to midnight UTC).
    
    Args:
        bucket_name: GCS bucket name
        prefix: GCS prefix (e.g., "images")
        target_date: Date in YYYY-MM-DD format (default: yesterday)
        output_dir: Directory to save package (default: data/packages)
        format: Archive format ("zip" or "tar.gz")
    
    Returns:
        Path to created archive file
    """
    if target_date is None:
        # Default to yesterday
        yesterday = datetime.utcnow() - timedelta(days=1)
        target_date = yesterday.strftime("%Y-%m-%d")
    
    # Parse target date
    date_obj = datetime.strptime(target_date, "%Y-%m-%d")
    date_start = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
    date_end = date_start + timedelta(days=1)
    
    LOGGER.info("Packaging images from %s (UTC)", target_date)
    LOGGER.info("Time range: %s to %s", date_start.isoformat(), date_end.isoformat())
    
    # Connect to GCS
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    
    # Find all images from target date
    blobs = list(bucket.list_blobs(prefix=prefix))
    daily_images: dict[str, list[storage.Blob]] = defaultdict(list)
    total_images = 0
    
    for blob in blobs:
        if not blob.name.endswith((".jpg", ".jpeg")):
            continue
        
        timestamp = parse_timestamp_from_path(blob.name)
        if not timestamp:
            continue
        
        # Check if within date range (midnight to midnight UTC)
        if date_start <= timestamp < date_end:
            # Extract camera ID from path
            parts = blob.name.split("/")
            if len(parts) >= 3:
                camera_id = parts[-2]
                daily_images[camera_id].append(blob)
                total_images += 1
    
    if total_images == 0:
        LOGGER.warning("No images found for date %s", target_date)
        return None
    
    LOGGER.info("Found %d images from %d cameras for %s", total_images, len(daily_images), target_date)
    
    # Create output directory
    if output_dir is None:
        output_dir = Path("data/packages")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create archive
    archive_name = f"pax-images-{target_date}.{format}"
    archive_path = output_dir / archive_name
    
    LOGGER.info("Creating archive: %s", archive_path)
    
    if format == "zip":
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for camera_id, blobs in sorted(daily_images.items()):
                for blob in sorted(blobs, key=lambda b: b.name):
                    # Download blob content
                    image_data = blob.download_as_bytes()
                    # Store in archive with camera_id/date structure
                    archive_path_internal = f"{target_date}/{camera_id}/{Path(blob.name).name}"
                    zf.writestr(archive_path_internal, image_data)
                    LOGGER.debug("Added %s", archive_path_internal)
    else:  # tar.gz
        import gzip
        with tarfile.open(archive_path, "w:gz") as tf:
            for camera_id, blobs in sorted(daily_images.items()):
                for blob in sorted(blobs, key=lambda b: b.name):
                    # Download blob content
                    image_data = blob.download_as_bytes()
                    # Create tarinfo
                    archive_path_internal = f"{target_date}/{camera_id}/{Path(blob.name).name}"
                    tarinfo = tarfile.TarInfo(name=archive_path_internal)
                    tarinfo.size = len(image_data)
                    tarinfo.mtime = blob.time_created.timestamp() if blob.time_created else 0
                    # Add to archive
                    tf.addfile(tarinfo, fileobj=__import__("io").BytesIO(image_data))
                    LOGGER.debug("Added %s", archive_path_internal)
    
    archive_size_mb = archive_path.stat().st_size / (1024 * 1024)
    LOGGER.info("Created archive: %s (%.2f MB)", archive_path, archive_size_mb)
    
    # Create manifest
    manifest = {
        "date": target_date,
        "total_images": total_images,
        "cameras": len(daily_images),
        "images_per_camera": {cam_id: len(blobs) for cam_id, blobs in daily_images.items()},
        "archive_path": str(archive_path),
        "archive_size_bytes": archive_path.stat().st_size,
        "created_at": datetime.utcnow().isoformat(),
    }
    
    manifest_path = output_dir / f"manifest-{target_date}.json"
    with manifest_path.open("w") as f:
        json.dump(manifest, f, indent=2)
    
    LOGGER.info("Created manifest: %s", manifest_path)
    
    return archive_path


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
        "--date",
        help="Date to package (YYYY-MM-DD, default: yesterday)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory (default: data/packages)",
    )
    parser.add_argument(
        "--format",
        choices=["zip", "tar.gz"],
        default="zip",
        help="Archive format (default: zip)",
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
    
    try:
        archive_path = package_daily_images(
            bucket_name=bucket_name,
            prefix=args.prefix,
            target_date=args.date,
            output_dir=args.output_dir,
            format=args.format,
        )
        
        if archive_path:
            print(f"\n✅ Created archive: {archive_path}")
            print(f"   Size: {archive_path.stat().st_size / (1024*1024):.2f} MB")
            return 0
        else:
            print(f"\n⚠️  No images found for date {args.date or 'yesterday'}")
            return 1
        
    except Exception as e:
        LOGGER.exception("Failed to package images: %s", e)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

