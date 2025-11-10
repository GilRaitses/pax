#!/usr/bin/env python3
"""Check for missing cameras and their status.

Identifies cameras in the manifest that are not being collected,
and determines why (offline, not in API, etc.).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def check_missing_cameras():
    """Check which cameras are missing and why."""
    # Load manifest
    manifest_path = Path("data/manifests/corridor_cameras_numbered.json")
    if not manifest_path.exists():
        print(f"ERROR: Manifest not found: {manifest_path}")
        return

    manifest = json.load(open(manifest_path))
    manifest_cameras = manifest.get("cameras", [])
    print(f"Total cameras in manifest: {len(manifest_cameras)}")

    # Fetch all cameras from API (including offline)
    print("\nFetching cameras from NYCTMC API...")
    api_url = "https://webcams.nyctmc.org/api/cameras"
    try:
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        all_cameras = response.json()
        print(f"Total cameras from API: {len(all_cameras)}")
    except Exception as e:
        print(f"ERROR: Failed to fetch cameras from API: {e}")
        return

    # Create maps
    api_camera_map = {cam["id"]: cam for cam in all_cameras}
    manifest_camera_ids = {cam.get("id") for cam in manifest_cameras}

    # Categorize cameras
    missing_from_api = []
    offline_cameras = []
    online_cameras = []

    for cam in manifest_cameras:
        cam_id = cam.get("id")
        cam_number = cam.get("number")
        cam_name = cam.get("name", "")

        if cam_id not in api_camera_map:
            missing_from_api.append(
                {
                    "number": cam_number,
                    "id": cam_id,
                    "name": cam_name,
                }
            )
        else:
            api_cam = api_camera_map[cam_id]
            is_online = api_cam.get("isOnline") == "true"
            if is_online:
                online_cameras.append(
                    {
                        "number": cam_number,
                        "id": cam_id,
                        "name": cam_name,
                    }
                )
            else:
                offline_cameras.append(
                    {
                        "number": cam_number,
                        "id": cam_id,
                        "name": cam_name,
                        "isOnline": api_cam.get("isOnline", "N/A"),
                    }
                )

    # Print report
    print("\n" + "=" * 60)
    print("MISSING CAMERA ANALYSIS")
    print("=" * 60)
    print(f"\nOnline cameras (will be collected): {len(online_cameras)}")
    print(f"Offline cameras (will be skipped): {len(offline_cameras)}")
    print(f"Missing from API (not found): {len(missing_from_api)}")

    if offline_cameras:
        print("\n" + "-" * 60)
        print("OFFLINE CAMERAS (will be skipped by collector):")
        print("-" * 60)
        for cam in sorted(offline_cameras, key=lambda x: x["number"]):
            print(f"  Camera #{cam['number']}: {cam['name']}")
            print(f"    ID: {cam['id']}")
            print(f"    Status: {cam['isOnline']}")
            print()

    if missing_from_api:
        print("\n" + "-" * 60)
        print("MISSING FROM API (not found in API response):")
        print("-" * 60)
        for cam in sorted(missing_from_api, key=lambda x: x["number"]):
            print(f"  Camera #{cam['number']}: {cam['name']}")
            print(f"    ID: {cam['id']}")
            print()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Expected to collect: {len(online_cameras)}/{len(manifest_cameras)} cameras")
    print(f"Success rate: {len(online_cameras)/len(manifest_cameras)*100:.1f}%")

    if offline_cameras:
        print(f"\n⚠️  {len(offline_cameras)} camera(s) are offline and will be skipped")
        print("   These cameras may come back online later")
        print("   The collector filters to only online cameras for reliability")

    if missing_from_api:
        print(f"\n❌ {len(missing_from_api)} camera(s) are not in the API")
        print("   These may need to be removed from the manifest")


if __name__ == "__main__":
    check_missing_cameras()

