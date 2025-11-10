#!/usr/bin/env python3
"""Download all images from today's collection runs.

Downloads images from GCS that were collected today (since last download).
Launches a progress monitor in a separate terminal window.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def get_todays_date_et() -> str:
    """Get today's date string in Eastern Time."""
    today_et = datetime.now(ZoneInfo("America/New_York"))
    return today_et.strftime("%Y-%m-%d")


def list_todays_images_gcs(bucket: str = "pax-nyc-images", prefix: str = "images") -> list[str]:
    """List all images from today in GCS using Google Cloud Storage API."""
    print("Fetching today's images from GCS...")
    
    try:
        from google.cloud import storage
        
        client = storage.Client()
        bucket_obj = client.bucket(bucket)
        
        # Get today's date range in ET
        today_et = datetime.now(ZoneInfo("America/New_York"))
        today_start = today_et.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_et.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Convert to UTC for comparison with blob.time_created
        today_start_utc = today_start.astimezone(ZoneInfo("UTC"))
        today_end_utc = today_end.astimezone(ZoneInfo("UTC"))
        
        # List all blobs
        blobs = list(bucket_obj.list_blobs(prefix=prefix))
        
        # Filter to today's images
        today_images = []
        for blob in blobs:
            if not blob.name.endswith((".jpg", ".jpeg")):
                continue
            
            # Check if blob was created today (by time_created)
            if blob.time_created:
                created_utc = blob.time_created
                if today_start_utc <= created_utc <= today_end_utc:
                    today_images.append(f"gs://{bucket}/{blob.name}")
        
        print(f"Found {len(today_images)} images from today in GCS")
        return today_images
        
    except ImportError:
        print("ERROR: google-cloud-storage not installed. Using gsutil fallback...")
        # Fallback to gsutil
        gcs_path = f"gs://{bucket}/{prefix}/"
        try:
            result = subprocess.run(
                ["gsutil", "ls", "-r", gcs_path],
                capture_output=True,
                text=True,
                timeout=120,
            )
            
            if result.returncode != 0:
                print(f"ERROR: Failed to list GCS: {result.stderr}")
                return []
            
            # Parse filename format: YYYYMMDDTHHMMSS.jpg
            today_et = datetime.now(ZoneInfo("America/New_York"))
            today_str = today_et.strftime("%Y%m%d")
            
            lines = result.stdout.strip().split("\n")
            today_images = [
                line.strip()
                for line in lines
                if today_str in line and line.strip().endswith(".jpg")
            ]
            
            print(f"Found {len(today_images)} images from today in GCS")
            return today_images
            
        except Exception as e:
            print(f"ERROR: Failed to list GCS: {e}")
            return []
    except Exception as e:
        print(f"ERROR: Failed to list GCS: {e}")
        return []


def get_local_image_paths(local_dir: Path) -> set[str]:
    """Get set of local image paths (relative to local_dir)."""
    if not local_dir.exists():
        return set()
    
    local_images = set()
    for img_path in local_dir.rglob("*.jpg"):
        # Get relative path from local_dir
        rel_path = img_path.relative_to(local_dir)
        local_images.add(str(rel_path))
    
    return local_images


def download_image(gcs_path: str, local_path: Path) -> bool:
    """Download a single image from GCS."""
    try:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["gsutil", "cp", gcs_path, str(local_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        if result.returncode == 0:
            return True
        else:
            print(f"  ERROR downloading {gcs_path}: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"  ERROR downloading {gcs_path}: {e}")
        return False


def launch_progress_monitor(local_dir: Path, expected_total: int, date_filter: str | None = None) -> None:
    """Launch progress monitor in a separate terminal window."""
    script_dir = Path(__file__).parent
    monitor_script = script_dir / "open_download_monitor.sh"
    
    if not monitor_script.exists():
        print("⚠️  Progress monitor script not found, skipping monitor launch")
        return
    
    try:
        # Make script executable
        os.chmod(monitor_script, 0o755)
        
        # Build command arguments
        args = [str(monitor_script), str(local_dir), str(expected_total), "2.0"]
        if date_filter:
            args.append(date_filter)
        
        # Launch monitor in background
        subprocess.Popen(
            args,
            cwd=script_dir.parent.parent,
        )
        print(f"✅ Progress monitor launched in separate terminal window")
        print(f"   Monitoring: {local_dir}")
        print(f"   Expected: {expected_total} images")
        if date_filter:
            print(f"   Date filter: {date_filter}")
    except Exception as e:
        print(f"⚠️  Failed to launch progress monitor: {e}")
        print("   Download will continue without monitor")


def download_todays_images(
    bucket: str = "pax-nyc-images",
    prefix: str = "images",
    local_dir: Path | None = None,
    dry_run: bool = False,
    launch_monitor: bool = True,
) -> None:
    """Download all images from today's collection runs."""
    if local_dir is None:
        local_dir = Path("data/raw/images")
    
    local_dir = Path(local_dir)
    print(f"Local directory: {local_dir}")
    
    # Get today's images from GCS
    gcs_images = list_todays_images_gcs(bucket, prefix)
    
    if not gcs_images:
        print("No images found from today in GCS")
        return
    
    # Get local images
    print("\nChecking local images...")
    local_images = get_local_image_paths(local_dir)
    print(f"Found {len(local_images)} existing local images")
    
    # Determine which images to download
    images_to_download = []
    for gcs_path in gcs_images:
        # Extract relative path from GCS path
        # Format: gs://bucket/prefix/camera_id/timestamp.jpg
        parts = gcs_path.replace(f"gs://{bucket}/{prefix}/", "").split("/")
        if len(parts) >= 2:
            rel_path = "/".join(parts)
            if rel_path not in local_images:
                images_to_download.append((gcs_path, rel_path))
    
    print(f"\nImages to download: {len(images_to_download)}")
    
    if dry_run:
        print("\nDRY RUN - Would download:")
        for gcs_path, rel_path in images_to_download[:10]:
            print(f"  {gcs_path} -> {local_dir / rel_path}")
        if len(images_to_download) > 10:
            print(f"  ... and {len(images_to_download) - 10} more")
        return
    
    # Get today's date for filtering (YYYYMMDD format)
    today_et = datetime.now(ZoneInfo("America/New_York"))
    today_date_filter = today_et.strftime("%Y%m%d")
    
    # Launch progress monitor if requested
    if launch_monitor and len(images_to_download) > 0:
        print("\nLaunching progress monitor...")
        launch_progress_monitor(local_dir, len(images_to_download), today_date_filter)
        print("Waiting 2 seconds for monitor to start...")
        import time
        time.sleep(2)
        print()
    
    # Download images
    print("=" * 60)
    print("DOWNLOADING IMAGES")
    print("=" * 60)
    print(f"Total to download: {len(images_to_download)}")
    print(f"Progress monitor is running in separate window")
    print("=" * 60)
    print()
    
    downloaded = 0
    failed = 0
    
    for i, (gcs_path, rel_path) in enumerate(images_to_download, 1):
        local_path = local_dir / rel_path
        
        # Print progress every 50 images or at milestones
        if (i % 50 == 0) or (i == len(images_to_download)) or (i == 1):
            print(f"[{i}/{len(images_to_download)}] ({i/len(images_to_download)*100:.1f}%) Downloading...")
        
        if download_image(gcs_path, local_path):
            downloaded += 1
        else:
            failed += 1
    
    print("\n" + "=" * 60)
    print("DOWNLOAD SUMMARY")
    print("=" * 60)
    print(f"Total images in GCS (today): {len(gcs_images)}")
    print(f"Already downloaded: {len(gcs_images) - len(images_to_download)}")
    print(f"Downloaded: {downloaded}")
    print(f"Failed: {failed}")
    print(f"Local directory: {local_dir}")
    print("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Download today's images from GCS")
    parser.add_argument(
        "--bucket",
        default="pax-nyc-images",
        help="GCS bucket name (default: pax-nyc-images)",
    )
    parser.add_argument(
        "--prefix",
        default="images",
        help="GCS prefix (default: images)",
    )
    parser.add_argument(
        "--local-dir",
        type=Path,
        default=Path("data/raw/images"),
        help="Local directory to save images (default: data/raw/images)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without actually downloading",
    )
    parser.add_argument(
        "--no-monitor",
        action="store_true",
        help="Don't launch progress monitor window",
    )
    
    args = parser.parse_args()
    
    download_todays_images(
        bucket=args.bucket,
        prefix=args.prefix,
        local_dir=args.local_dir,
        dry_run=args.dry_run,
        launch_monitor=not args.no_monitor,
    )


if __name__ == "__main__":
    main()

