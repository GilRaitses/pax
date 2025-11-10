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


def list_todays_images_gcs(
    bucket: str = "pax-nyc-images",
    prefix: str = "images",
    start_hour: int = 12,
    end_hour: int = 18,
) -> list[tuple[str, int]]:
    """List all images from today in GCS within specified time range.
    
    Returns list of tuples: (gcs_path, file_size_bytes)
    """
    print(f"Fetching today's images from GCS (12pm-6pm ET)...")
    
    try:
        from google.cloud import storage
        
        client = storage.Client()
        bucket_obj = client.bucket(bucket)
        
        # Get today's date range in ET (12pm-6pm)
        today_et = datetime.now(ZoneInfo("America/New_York"))
        today_start = today_et.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        today_end = today_et.replace(hour=end_hour, minute=59, second=59, microsecond=999999)
        
        # Convert to UTC for comparison with blob.time_created
        today_start_utc = today_start.astimezone(ZoneInfo("UTC"))
        today_end_utc = today_end.astimezone(ZoneInfo("UTC"))
        
        # List all blobs
        blobs = list(bucket_obj.list_blobs(prefix=prefix))
        
        # Filter to today's images in time range
        today_images = []
        for blob in blobs:
            if not blob.name.endswith((".jpg", ".jpeg")):
                continue
            
            # Check if blob was created in the time range (by time_created)
            if blob.time_created:
                created_utc = blob.time_created
                if today_start_utc <= created_utc <= today_end_utc:
                    today_images.append((f"gs://{bucket}/{blob.name}", blob.size))
        
        print(f"Found {len(today_images)} images from {start_hour}:00-{end_hour}:59 ET today in GCS")
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


def get_local_image_paths(local_dir: Path) -> dict[str, int]:
    """Get dict of local image paths and their sizes (relative to local_dir).
    
    Returns dict mapping relative path to file size in bytes.
    This allows us to check if files are partially downloaded (small size).
    """
    if not local_dir.exists():
        return {}
    
    local_images = {}
    for img_path in local_dir.rglob("*.jpg"):
        try:
            # Get relative path from local_dir
            rel_path = img_path.relative_to(local_dir)
            # Get file size to detect partial downloads
            file_size = img_path.stat().st_size
            local_images[str(rel_path)] = file_size
        except (OSError, ValueError):
            # Skip files that can't be accessed or are invalid
            continue
    
    return local_images


def download_image(gcs_path: str, local_path: Path, expected_size: int | None = None) -> bool:
    """Download a single image from GCS.
    
    If file exists, checks if it's complete by comparing sizes.
    Re-downloads if file is missing or smaller than expected.
    """
    try:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if file already exists and is complete
        if local_path.exists():
            if expected_size is not None:
                local_size = local_path.stat().st_size
                # If file size matches expected size, skip (already downloaded)
                if local_size == expected_size:
                    return True
                # If file is smaller, it's partial - delete and re-download
                elif local_size < expected_size:
                    print(f"  Re-downloading partial file: {local_path.name} ({local_size}/{expected_size} bytes)")
                    local_path.unlink()
            else:
                # No expected size, check if file is reasonable size (>1KB)
                local_size = local_path.stat().st_size
                if local_size > 1024:  # Assume >1KB is complete
                    return True
                else:
                    print(f"  Re-downloading suspiciously small file: {local_path.name} ({local_size} bytes)")
                    local_path.unlink()
        
        # Download the file
        result = subprocess.run(
            ["gsutil", "cp", gcs_path, str(local_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        if result.returncode == 0:
            # Verify download completed successfully
            if local_path.exists():
                if expected_size is not None:
                    local_size = local_path.stat().st_size
                    if local_size != expected_size:
                        print(f"  WARNING: Size mismatch after download: {local_size}/{expected_size} bytes")
                        return False
                return True
            else:
                print(f"  ERROR: File not found after download")
                return False
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
    start_hour: int = 12,
    end_hour: int = 18,
) -> None:
    """Download all images from today's collection runs (12pm-6pm ET by default)."""
    if local_dir is None:
        local_dir = Path("data/raw/images")
    
    local_dir = Path(local_dir)
    print(f"Local directory: {local_dir}")
    print(f"Time range: {start_hour}:00-{end_hour}:59 ET today")
    
    # Get today's images from GCS (with file sizes)
    gcs_images_with_sizes = list_todays_images_gcs(bucket, prefix, start_hour, end_hour)
    
    if not gcs_images_with_sizes:
        print("No images found from specified time range in GCS")
        return
    
    # Get local images (with sizes)
    print("\nChecking local images...")
    local_images = get_local_image_paths(local_dir)
    print(f"Found {len(local_images)} existing local images")
    
    # Determine which images to download
    # Re-download if: missing, partial (smaller size), or size mismatch
    images_to_download = []
    for gcs_path, gcs_size in gcs_images_with_sizes:
        # Extract relative path from GCS path
        # Format: gs://bucket/prefix/camera_id/timestamp.jpg
        parts = gcs_path.replace(f"gs://{bucket}/{prefix}/", "").split("/")
        if len(parts) >= 2:
            rel_path = "/".join(parts)
            local_path = local_dir / rel_path
            
            # Check if we need to download
            needs_download = True
            if rel_path in local_images:
                local_size = local_images[rel_path]
                # File exists and size matches - skip
                if local_size == gcs_size:
                    needs_download = False
                # File exists but size is different - re-download
                elif local_size < gcs_size:
                    print(f"  Found partial file: {rel_path} ({local_size}/{gcs_size} bytes) - will re-download")
            
            if needs_download:
                images_to_download.append((gcs_path, rel_path, gcs_size))
    
    print(f"\nImages to download: {len(images_to_download)}")
    if len(gcs_images_with_sizes) - len(images_to_download) > 0:
        print(f"Already complete: {len(gcs_images_with_sizes) - len(images_to_download)}")
    
    if dry_run:
        print("\nDRY RUN - Would download:")
        for gcs_path, rel_path, gcs_size in images_to_download[:10]:
            local_path = local_dir / rel_path
            if local_path.exists():
                local_size = local_path.stat().st_size
                print(f"  {gcs_path} -> {local_path} (re-download: {local_size}/{gcs_size} bytes)")
            else:
                print(f"  {gcs_path} -> {local_path} (new: {gcs_size} bytes)")
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
    redownloaded = 0
    
    for i, (gcs_path, rel_path, gcs_size) in enumerate(images_to_download, 1):
        local_path = local_dir / rel_path
        
        # Print progress every 50 images or at milestones
        if (i % 50 == 0) or (i == len(images_to_download)) or (i == 1):
            print(f"[{i}/{len(images_to_download)}] ({i/len(images_to_download)*100:.1f}%) Downloading...")
        
        # Check if this is a re-download
        is_redownload = local_path.exists()
        
        if download_image(gcs_path, local_path, gcs_size):
            downloaded += 1
            if is_redownload:
                redownloaded += 1
        else:
            failed += 1
    
    print("\n" + "=" * 60)
    print("DOWNLOAD SUMMARY")
    print("=" * 60)
    print(f"Total images in GCS ({start_hour}:00-{end_hour}:59 ET today): {len(gcs_images_with_sizes)}")
    print(f"Already complete: {len(gcs_images_with_sizes) - len(images_to_download)}")
    print(f"Downloaded: {downloaded}")
    if redownloaded > 0:
        print(f"  (Re-downloaded: {redownloaded} partial files)")
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
    parser.add_argument(
        "--start-hour",
        type=int,
        default=12,
        help="Start hour (0-23) in ET (default: 12 for 12pm)",
    )
    parser.add_argument(
        "--end-hour",
        type=int,
        default=18,
        help="End hour (0-23) in ET (default: 18 for 6pm)",
    )
    
    args = parser.parse_args()
    
    download_todays_images(
        bucket=args.bucket,
        prefix=args.prefix,
        local_dir=args.local_dir,
        dry_run=args.dry_run,
        launch_monitor=not args.no_monitor,
        start_hour=args.start_hour,
        end_hour=args.end_hour,
    )


if __name__ == "__main__":
    main()

