#!/usr/bin/env python3
"""Check GCS for images from cameras in purple and red zones, identify date gaps."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from google.cloud import storage
from shapely.geometry import Point, Polygon

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


def get_purple_zone_corners() -> dict[str, tuple[float, float]]:
    """Get purple zone corners: 34th-66th St, 3rd-9th/Amsterdam."""
    # These are the corners we found earlier
    return {
        "NW": (-73.981573, 40.773602),  # Columbus/Amsterdam & 66th
        "NE": (-73.963402, 40.765911),  # 3rd Ave & 66th
        "SE": (-73.978124, 40.745727),  # 3rd Ave & 34th
        "SW": (-73.996303, 40.753389),  # 9th Ave & 34th
    }


def get_red_zone_corners() -> dict[str, tuple[float, float]]:
    """Get red zone corners: 40th-61st St, Lex-8th/CPW."""
    return {
        "NW": (-73.981023, 40.769273),  # CPW & 61st
        "NE": (-73.967271, 40.763480),  # Lexington & 61st
        "SE": (-73.976986, 40.750157),  # Lexington & 40th
        "SW": (-73.990726, 40.755950),  # 8th Ave & 40th
    }


def filter_cameras_in_zone(
    cameras: list[dict],
    zone_corners: dict[str, tuple[float, float]],
) -> list[dict]:
    """Filter cameras within zone bounds."""
    if len(zone_corners) != 4:
        return []
    
    polygon = Polygon([
        zone_corners["NW"],
        zone_corners["NE"],
        zone_corners["SE"],
        zone_corners["SW"],
    ])
    
    buffered_polygon = polygon.buffer(0.0003)  # ~33 meters
    
    filtered = []
    for cam in cameras:
        lat = cam.get("latitude")
        lon = cam.get("longitude")
        if lat is None or lon is None:
            continue
        
        point = Point(lon, lat)
        if buffered_polygon.intersects(point):
            filtered.append(cam)
    
    return filtered


def check_zone_images_gcs(
    bucket_name: str,
    prefix: str = "images",
    purple_zone: bool = True,
    red_zone: bool = True,
) -> dict:
    """Check GCS for images from cameras in specified zones."""
    from ..data_collection.camera_client import CameraAPIClient
    
    # Get all cameras from API
    try:
        client = CameraAPIClient(PaxSettings())
        all_cameras = client.list_cameras()
        LOGGER.info("Fetched %d cameras from API", len(all_cameras))
    except Exception as e:
        LOGGER.error("Failed to fetch cameras: %s", e)
        # Fallback: try requests directly
        try:
            import requests
            api_url = "https://webcams.nyctmc.org/api/cameras"
            response = requests.get(api_url, timeout=30)
            response.raise_for_status()
            all_cameras = response.json()
            all_cameras = [cam for cam in all_cameras if cam.get("isOnline") == "true"]
            LOGGER.info("Fetched %d cameras from API directly", len(all_cameras))
        except Exception as e2:
            LOGGER.error("Failed to fetch cameras: %s", e2)
            return {"error": "Failed to fetch cameras"}
    
    # Filter cameras by zone
    purple_cameras = []
    red_cameras = []
    
    if purple_zone:
        purple_corners = get_purple_zone_corners()
        purple_cameras = filter_cameras_in_zone(all_cameras, purple_corners)
        LOGGER.info("Found %d cameras in purple zone", len(purple_cameras))
    
    if red_zone:
        red_corners = get_red_zone_corners()
        red_cameras = filter_cameras_in_zone(all_cameras, red_corners)
        LOGGER.info("Found %d cameras in red zone", len(red_cameras))
    
    # Get camera IDs
    purple_camera_ids = {cam.get("id") for cam in purple_cameras if cam.get("id")}
    red_camera_ids = {cam.get("id") for cam in red_cameras if cam.get("id")}
    
    # Check GCS
    gcs_client = storage.Client()
    bucket = gcs_client.bucket(bucket_name)
    
    LOGGER.info("Listing blobs in gs://%s/%s", bucket_name, prefix)
    blobs = list(bucket.list_blobs(prefix=prefix))
    LOGGER.info("Found %d total blobs", len(blobs))
    
    # Track images by zone and date
    purple_images_by_date: dict[str, int] = defaultdict(int)
    red_images_by_date: dict[str, int] = defaultdict(int)
    purple_camera_dates: dict[str, set[str]] = defaultdict(set)
    red_camera_dates: dict[str, set[str]] = defaultdict(set)
    
    total_purple_images = 0
    total_red_images = 0
    
    for blob in blobs:
        if not blob.name.endswith((".jpg", ".jpeg")):
            continue
        
        # Extract camera ID from path: images/camera-id/timestamp.jpg
        parts = blob.name.split("/")
        if len(parts) < 3:
            continue
        
        camera_id = parts[-2]
        timestamp = parse_timestamp_from_path(blob.name)
        
        if not timestamp:
            continue
        
        date_str = timestamp.strftime("%Y-%m-%d")
        
        # Check if camera is in purple zone
        if camera_id in purple_camera_ids:
            purple_images_by_date[date_str] += 1
            purple_camera_dates[camera_id].add(date_str)
            total_purple_images += 1
        
        # Check if camera is in red zone
        if camera_id in red_camera_ids:
            red_images_by_date[date_str] += 1
            red_camera_dates[camera_id].add(date_str)
            total_red_images += 1
    
    # Find date ranges and gaps
    all_purple_dates = sorted(purple_images_by_date.keys())
    all_red_dates = sorted(red_images_by_date.keys())
    
    purple_date_range = {
        "earliest": all_purple_dates[0] if all_purple_dates else None,
        "latest": all_purple_dates[-1] if all_purple_dates else None,
        "total_days": len(all_purple_dates),
    }
    
    red_date_range = {
        "earliest": all_red_dates[0] if all_red_dates else None,
        "latest": all_red_dates[-1] if all_red_dates else None,
        "total_days": len(all_red_dates),
    }
    
    # Find gaps (missing dates)
    def find_date_gaps(dates: list[str]) -> list[str]:
        if not dates:
            return []
        
        gaps = []
        start_date = datetime.strptime(dates[0], "%Y-%m-%d")
        end_date = datetime.strptime(dates[-1], "%Y-%m-%d")
        date_set = set(dates)
        
        current = start_date
        while current <= end_date:
            date_str = current.strftime("%Y-%m-%d")
            if date_str not in date_set:
                gaps.append(date_str)
            current += timedelta(days=1)
        
        return gaps
    
    purple_gaps = find_date_gaps(all_purple_dates)
    red_gaps = find_date_gaps(all_red_dates)
    
    result = {
        "bucket": bucket_name,
        "prefix": prefix,
        "purple_zone": {
            "cameras": len(purple_camera_ids),
            "total_images": total_purple_images,
            "date_range": purple_date_range,
            "images_by_date": dict(sorted(purple_images_by_date.items())),
            "missing_dates": purple_gaps,
            "cameras_by_date": {
                cam_id: sorted(dates) for cam_id, dates in purple_camera_dates.items()
            },
        },
        "red_zone": {
            "cameras": len(red_camera_ids),
            "total_images": total_red_images,
            "date_range": red_date_range,
            "images_by_date": dict(sorted(red_images_by_date.items())),
            "missing_dates": red_gaps,
            "cameras_by_date": {
                cam_id: sorted(dates) for cam_id, dates in red_camera_dates.items()
            },
        },
        "checked_at": datetime.now().isoformat(),
    }
    
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bucket",
        help="GCS bucket name (default: from settings)",
    )
    parser.add_argument(
        "--prefix",
        help="GCS prefix/folder (default: 'images')",
        default="images",
    )
    parser.add_argument(
        "--purple-only",
        action="store_true",
        help="Check only purple zone",
    )
    parser.add_argument(
        "--red-only",
        action="store_true",
        help="Check only red zone",
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
    
    args = parser.parse_args(argv)
    logging.basicConfig(level=args.log_level.upper(), format="%(levelname)s: %(message)s")
    
    settings = PaxSettings()
    bucket_name = args.bucket or settings.remote.bucket
    
    # Default from deployment config if not set
    if not bucket_name:
        bucket_name = "pax-nyc-images"
        LOGGER.info("Using default bucket from deployment config: %s", bucket_name)
    
    purple_zone = not args.red_only
    red_zone = not args.purple_only
    
    try:
        result = check_zone_images_gcs(
            bucket_name=bucket_name,
            prefix=args.prefix,
            purple_zone=purple_zone,
            red_zone=red_zone,
        )
        
        if "error" in result:
            LOGGER.error(result["error"])
            return 1
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            # Pretty print
            print("\n" + "=" * 70)
            print(f"GCS Zone Image Status: gs://{result['bucket']}/{result['prefix']}")
            print("=" * 70)
            
            if purple_zone:
                purple = result["purple_zone"]
                print(f"\n🟣 PURPLE ZONE (Camera Corridor):")
                print(f"  Cameras: {purple['cameras']}")
                print(f"  Total images: {purple['total_images']:,}")
                if purple["date_range"]["earliest"]:
                    print(f"  Date range: {purple['date_range']['earliest']} to {purple['date_range']['latest']}")
                    print(f"  Days with images: {purple['date_range']['total_days']}")
                    if purple["missing_dates"]:
                        print(f"  Missing dates: {len(purple['missing_dates'])}")
                        if len(purple["missing_dates"]) <= 10:
                            print(f"    {', '.join(purple['missing_dates'])}")
                        else:
                            print(f"    {', '.join(purple['missing_dates'][:10])} ... ({len(purple['missing_dates'])} total)")
                    else:
                        print(f"  ✓ No gaps in date range")
                    print(f"\n  Last 10 days:")
                    for date, count in list(sorted(purple["images_by_date"].items()))[-10:]:
                        print(f"    {date}: {count:,} images")
            
            if red_zone:
                red = result["red_zone"]
                print(f"\n🔴 RED ZONE (Problem Space):")
                print(f"  Cameras: {red['cameras']}")
                print(f"  Total images: {red['total_images']:,}")
                if red["date_range"]["earliest"]:
                    print(f"  Date range: {red['date_range']['earliest']} to {red['date_range']['latest']}")
                    print(f"  Days with images: {red['date_range']['total_days']}")
                    if red["missing_dates"]:
                        print(f"  Missing dates: {len(red['missing_dates'])}")
                        if len(red["missing_dates"]) <= 10:
                            print(f"    {', '.join(red['missing_dates'])}")
                        else:
                            print(f"    {', '.join(red['missing_dates'][:10])} ... ({len(red['missing_dates'])} total)")
                    else:
                        print(f"  ✓ No gaps in date range")
                    print(f"\n  Last 10 days:")
                    for date, count in list(sorted(red["images_by_date"].items()))[-10:]:
                        print(f"    {date}: {count:,} images")
            
            print(f"\nChecked at: {result['checked_at']}")
            print("=" * 70 + "\n")
        
        return 0
        
    except Exception as e:
        LOGGER.exception("Failed to check zone images: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())

