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


def count_local_images(local_dir: Path) -> dict:
    """Count images in local directory."""
    if not local_dir.exists():
        return {"total": 0, "by_camera": {}}
    
    total = 0
    by_camera = {}
    
    for img_path in local_dir.rglob("*.jpg"):
        total += 1
        # Extract camera ID from path
        parts = img_path.parts
        if len(parts) >= 2:
            camera_id = parts[-2]  # Parent directory is camera ID
            by_camera[camera_id] = by_camera.get(camera_id, 0) + 1
    
    return {"total": total, "by_camera": by_camera}


def monitor_progress(local_dir: Path, expected_total: int = 0, refresh_interval: float = 2.0):
    """Monitor download progress."""
    print("=" * 60)
    print("DOWNLOAD PROGRESS MONITOR")
    print("=" * 60)
    print(f"Local directory: {local_dir}")
    if expected_total > 0:
        print(f"Expected total: {expected_total} images")
    print(f"Refresh interval: {refresh_interval} seconds")
    print("=" * 60)
    print()
    
    last_count = 0
    start_time = time.time()
    
    try:
        while True:
            stats = count_local_images(local_dir)
            current_count = stats["total"]
            
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
            print(f"Images downloaded: {current_count}")
            if expected_total > 0:
                percentage = (current_count / expected_total * 100) if expected_total > 0 else 0
                print(f"Progress: {percentage:.1f}% ({current_count}/{expected_total})")
                remaining = expected_total - current_count
                if remaining > 0 and rate > 0:
                    eta_seconds = remaining / rate
                    eta_minutes = int(eta_seconds // 60)
                    eta_secs = int(eta_seconds % 60)
                    print(f"ETA: {eta_minutes}m {eta_secs}s")
            print()
            print(f"Average rate: {rate:.1f} images/second")
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
        final_stats = count_local_images(local_dir)
        print(f"\nFinal count: {final_stats['total']} images")
        if expected_total > 0:
            print(f"Expected: {expected_total} images")
            print(f"Remaining: {expected_total - final_stats['total']} images")


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
    
    args = parser.parse_args()
    
    monitor_progress(
        local_dir=args.local_dir,
        expected_total=args.expected_total,
        refresh_interval=args.refresh_interval,
    )


if __name__ == "__main__":
    main()

