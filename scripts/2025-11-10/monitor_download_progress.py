#!/usr/bin/env python3
"""Monitor download progress in real-time.

This script monitors the download progress by watching the local images directory
and displaying statistics.
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def count_local_images(local_dir: Path, date_filter: str | None = None) -> dict:
    """Count images in local directory, optionally filtered by date in filename."""
    if not local_dir.exists():
        return {"total": 0, "by_camera": {}}
    
    total = 0
    by_camera = {}
    
    for img_path in local_dir.rglob("*.jpg"):
        # Filter by date if specified (check filename format: YYYYMMDDTHHMMSS.jpg)
        if date_filter:
            filename = img_path.name
            if date_filter not in filename:
                continue
        
        total += 1
        # Extract camera ID from path
        parts = img_path.parts
        if len(parts) >= 2:
            camera_id = parts[-2]  # Parent directory is camera ID
            by_camera[camera_id] = by_camera.get(camera_id, 0) + 1
    
    return {"total": total, "by_camera": by_camera}


def monitor_progress(local_dir: Path, expected_total: int = 0, refresh_interval: float = 2.0, date_filter: str | None = None):
    """Monitor download progress."""
    print("=" * 60)
    print("DOWNLOAD PROGRESS MONITOR")
    print("=" * 60)
    print(f"Local directory: {local_dir}")
    if date_filter:
        print(f"Date filter: {date_filter} (only counting images from this date)")
    if expected_total > 0:
        print(f"Expected total: {expected_total} images")
    print(f"Refresh interval: {refresh_interval} seconds")
    print("=" * 60)
    print()
    
    last_count = 0
    start_time = time.time()
    initial_count = count_local_images(local_dir, date_filter)["total"]
    
    try:
        while True:
            stats = count_local_images(local_dir, date_filter)
            current_count = stats["total"]
            # Only count newly downloaded images (since monitor started)
            newly_downloaded = current_count - initial_count
            
            # Calculate rate
            elapsed = time.time() - start_time
            if elapsed > 0:
                rate = current_count / elapsed
                if current_count > last_count:
                    recent_rate = (current_count - last_count) / refresh_interval
                else:
                    recent_rate = 0.0
            else:
                rate = 0.0
                recent_rate = 0.0
            
            # Clear screen and print stats
            print("\033[2J\033[H", end="")  # Clear screen and move cursor to top
            print("=" * 60)
            print("DOWNLOAD PROGRESS MONITOR")
            print("=" * 60)
            print(f"Time: {datetime.now(ZoneInfo('America/New_York')).strftime('%Y-%m-%d %H:%M:%S %Z')}")
            print(f"Elapsed: {int(elapsed // 60)}m {int(elapsed % 60)}s")
            print()
            print(f"Total images in directory: {current_count}")
            if initial_count > 0:
                print(f"  (Started with: {initial_count}, Newly downloaded: {newly_downloaded})")
            else:
                print(f"  (Newly downloaded: {newly_downloaded})")
            
            if expected_total > 0:
                # Use newly_downloaded for progress calculation
                percentage = (newly_downloaded / expected_total * 100) if expected_total > 0 else 0
                percentage = min(percentage, 100.0)  # Cap at 100%
                print(f"Progress: {percentage:.1f}% ({newly_downloaded}/{expected_total})")
                remaining = max(expected_total - newly_downloaded, 0)
                if remaining > 0 and recent_rate > 0:
                    eta_seconds = remaining / recent_rate
                    eta_minutes = int(eta_seconds // 60)
                    eta_secs = int(eta_seconds % 60)
                    print(f"ETA: {eta_minutes}m {eta_secs}s")
            print()
            if elapsed > 0:
                print(f"Average rate: {newly_downloaded / elapsed:.1f} images/second")
            if recent_rate > 0:
                print(f"Recent rate: {recent_rate:.1f} images/second")
            print()
            
            if stats["by_camera"]:
                print(f"Cameras with images: {len(stats['by_camera'])}")
                # Show top 5 cameras
                sorted_cameras = sorted(stats["by_camera"].items(), key=lambda x: x[1], reverse=True)
                print("Top cameras:")
                for camera_id, count in sorted_cameras[:5]:
                    print(f"  {camera_id[:20]}...: {count} images")
            
            print()
            print("Press Ctrl+C to stop monitoring")
            print("=" * 60)
            
            last_count = current_count
            time.sleep(refresh_interval)
            
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")
        final_stats = count_local_images(local_dir, date_filter)
        final_newly_downloaded = final_stats['total'] - initial_count
        print(f"\nFinal count: {final_stats['total']} images total")
        print(f"Newly downloaded: {final_newly_downloaded} images")
        if expected_total > 0:
            print(f"Expected: {expected_total} images")
            print(f"Remaining: {max(expected_total - final_newly_downloaded, 0)} images")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Monitor download progress")
    parser.add_argument(
        "--local-dir",
        type=Path,
        default=Path("data/raw/images"),
        help="Local directory to monitor (default: data/raw/images)",
    )
    parser.add_argument(
        "--expected-total",
        type=int,
        default=0,
        help="Expected total number of images (for progress percentage)",
    )
    parser.add_argument(
        "--refresh-interval",
        type=float,
        default=2.0,
        help="Refresh interval in seconds (default: 2.0)",
    )
    parser.add_argument(
        "--date-filter",
        type=str,
        help="Date filter (YYYYMMDD) to only count images from this date (default: today)",
    )
    
    args = parser.parse_args()
    
    # Default to today's date if not specified
    if args.date_filter is None:
        today_et = datetime.now(ZoneInfo("America/New_York"))
        args.date_filter = today_et.strftime("%Y%m%d")
    
    monitor_progress(
        local_dir=args.local_dir,
        expected_total=args.expected_total,
        refresh_interval=args.refresh_interval,
        date_filter=args.date_filter,
    )


if __name__ == "__main__":
    main()

