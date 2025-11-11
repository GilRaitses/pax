#!/usr/bin/env python3
"""Download images for a specific 6-hour quarter of a day.

Quarters:
- Q1: 00:00-05:59 (midnight-6am)
- Q2: 06:00-11:59 (6am-noon)
- Q3: 12:00-17:59 (noon-6pm)
- Q4: 18:00-23:59 (6pm-midnight)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# Import the download function from the main script
sys.path.insert(0, str(Path(__file__).parent.parent / "2025-11-10"))
from download_todays_images import download_todays_images


def get_quarter_hours(quarter: int) -> tuple[int, int]:
    """Get start and end hours for a quarter.
    
    Args:
        quarter: 1, 2, 3, or 4
        
    Returns:
        (start_hour, end_hour) tuple
    """
    quarters = {
        1: (0, 5),   # Q1: midnight-5:59am
        2: (6, 11),  # Q2: 6am-11:59am
        3: (12, 17), # Q3: noon-5:59pm
        4: (18, 23), # Q4: 6pm-11:59pm
    }
    
    if quarter not in quarters:
        raise ValueError(f"Quarter must be 1, 2, 3, or 4, got {quarter}")
    
    return quarters[quarter]


def download_quarter(
    quarter: int,
    date: str | None = None,
    bucket: str = "pax-nyc-images",
    prefix: str = "images",
    local_dir: Path | None = None,
    dry_run: bool = False,
    launch_monitor: bool = True,
) -> None:
    """Download images for a specific quarter.
    
    Args:
        quarter: Quarter number (1-4)
        date: Date in YYYY-MM-DD format (default: today or yesterday based on quarter)
        bucket: GCS bucket name
        prefix: GCS prefix
        local_dir: Local directory to save images
        dry_run: If True, only show what would be downloaded
        launch_monitor: If True, launch progress monitor
    """
    now_et = datetime.now(ZoneInfo("America/New_York"))
    
    # Determine target date
    if date:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    else:
        # Default logic: if it's before noon and we want Q3/Q4, use yesterday
        # Otherwise use today
        start_hour, _ = get_quarter_hours(quarter)
        if quarter in (3, 4) and now_et.hour < 12:
            # Q3/Q4 before noon -> yesterday
            target_date = (now_et - timedelta(days=1)).date()
        else:
            target_date = now_et.date()
    
    # Get quarter hours
    start_hour, end_hour = get_quarter_hours(quarter)
    
    # Convert target_date to datetime at start of day in ET timezone
    target_datetime = datetime.combine(target_date, datetime.min.time())
    target_datetime = target_datetime.replace(tzinfo=ZoneInfo("America/New_York"))
    
    print("=" * 60)
    print(f"DOWNLOADING QUARTER {quarter}")
    print("=" * 60)
    print(f"Date: {target_date}")
    print(f"Time range: {start_hour:02d}:00-{end_hour:02d}:59 ET")
    print(f"Quarter: Q{quarter}")
    
    quarter_names = {
        1: "Q1 (midnight-6am)",
        2: "Q2 (6am-noon)",
        3: "Q3 (noon-6pm)",
        4: "Q4 (6pm-midnight)",
    }
    print(f"Description: {quarter_names[quarter]}")
    print("=" * 60)
    print()
    
    # Call the download function with the specific time range
    download_todays_images(
        bucket=bucket,
        prefix=prefix,
        local_dir=local_dir,
        dry_run=dry_run,
        launch_monitor=launch_monitor,
        start_hour=start_hour,
        end_hour=end_hour,
        target_date=target_date.strftime("%Y-%m-%d"),
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download images for a specific 6-hour quarter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Quarters:
  Q1: 00:00-05:59 (midnight-6am)
  Q2: 06:00-11:59 (6am-noon)
  Q3: 12:00-17:59 (noon-6pm)
  Q4: 18:00-23:59 (6pm-midnight)

Examples:
  # Download yesterday's Q3 (noon-6pm)
  python download_quarter.py 3 --date 2025-11-10

  # Download today's Q1 (midnight-6am)
  python download_quarter.py 1

  # Download today's Q2 (6am-noon) - wait until after noon
  python download_quarter.py 2
        """,
    )
    
    parser.add_argument(
        "quarter",
        type=int,
        choices=[1, 2, 3, 4],
        help="Quarter number (1-4)",
    )
    parser.add_argument(
        "--date",
        type=str,
        help="Date in YYYY-MM-DD format (default: today or yesterday based on quarter)",
    )
    parser.add_argument(
        "--bucket",
        type=str,
        default="pax-nyc-images",
        help="GCS bucket name (default: pax-nyc-images)",
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default="images",
        help="GCS prefix (default: images)",
    )
    parser.add_argument(
        "--local-dir",
        type=Path,
        default=None,
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
    
    download_quarter(
        quarter=args.quarter,
        date=args.date,
        bucket=args.bucket,
        prefix=args.prefix,
        local_dir=args.local_dir,
        dry_run=args.dry_run,
        launch_monitor=not args.no_monitor,
    )


if __name__ == "__main__":
    main()

