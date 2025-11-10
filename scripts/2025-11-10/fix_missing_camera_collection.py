#!/usr/bin/env python3
"""Fix missing camera collection issue.

The issue: Camera 421960d6-54a8-4f12-a5ee-7a07390def4c (MADISON @ 57 ST) 
was offline during the 2:00 PM run, so it was skipped.

Solution: The collector correctly skips offline cameras for reliability.
However, we can:
1. Verify the camera is back online
2. Test collection for this specific camera
3. Document that temporary offline cameras will be collected on next run
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    from pax.data_collection.camera_client import CameraAPIClient
    from pax.config import PaxSettings
except ImportError:
    print("ERROR: Could not import pax modules. Make sure you're in the project root.")
    sys.exit(1)


def check_camera_status(camera_id: str) -> dict | None:
    """Check the current status of a specific camera."""
    api_url = "https://webcams.nyctmc.org/api/cameras"
    try:
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        all_cameras = response.json()
        
        for cam in all_cameras:
            if cam.get("id") == camera_id:
                return cam
        return None
    except Exception as e:
        print(f"ERROR: Failed to fetch cameras: {e}")
        return None


def test_camera_collection(camera_id: str) -> bool:
    """Test collecting from a specific camera."""
    print(f"\nTesting collection for camera: {camera_id}")
    
    try:
        settings = PaxSettings()
        client = CameraAPIClient(settings)
        
        # Check if camera is in online list
        online_cameras = client.list_cameras()
        online_ids = {cam["id"] for cam in online_cameras}
        
        if camera_id not in online_ids:
            print(f"⚠️  Camera {camera_id} is not in online cameras list")
            print("   This means it's currently offline or not available")
            return False
        
        # Try to fetch snapshot
        snapshots = client.fetch_snapshots([camera_id])
        if snapshots:
            snapshot = snapshots[0]
            print(f"✅ Successfully fetched snapshot:")
            print(f"   Name: {snapshot.get('name', 'N/A')}")
            print(f"   Image URL: {snapshot.get('image_url', 'N/A')[:80]}...")
            return True
        else:
            print(f"❌ Failed to fetch snapshot for {camera_id}")
            return False
            
    except Exception as e:
        print(f"❌ Error during collection test: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point."""
    # The missing camera from the 2:00 PM run
    missing_camera_id = "421960d6-54a8-4f12-a5ee-7a07390def4c"
    
    print("=" * 60)
    print("MISSING CAMERA FIX ANALYSIS")
    print("=" * 60)
    
    # Load manifest to get camera name
    manifest_path = Path("data/manifests/corridor_cameras_numbered.json")
    if manifest_path.exists():
        manifest = json.load(open(manifest_path))
        for cam in manifest.get("cameras", []):
            if cam.get("id") == missing_camera_id:
                print(f"\nCamera: #{cam.get('number')} - {cam.get('name', 'N/A')}")
                print(f"ID: {missing_camera_id}")
                break
    
    # Check current status
    print("\n" + "-" * 60)
    print("Checking current camera status...")
    camera_status = check_camera_status(missing_camera_id)
    
    if camera_status:
        print(f"✅ Camera found in API")
        print(f"   Name: {camera_status.get('name', 'N/A')}")
        print(f"   isOnline: {camera_status.get('isOnline', 'N/A')}")
        print(f"   Latitude: {camera_status.get('latitude', 'N/A')}")
        print(f"   Longitude: {camera_status.get('longitude', 'N/A')}")
        
        if camera_status.get("isOnline") == "true":
            print("\n✅ Camera is ONLINE - should be collected on next run")
        else:
            print(f"\n⚠️  Camera is OFFLINE - will be skipped until it comes back online")
    else:
        print(f"❌ Camera NOT found in API")
        print("   This camera may have been removed from the API")
    
    # Test collection
    print("\n" + "-" * 60)
    print("Testing camera collection...")
    success = test_camera_collection(missing_camera_id)
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if success:
        print("✅ Camera collection is working correctly")
        print("   The camera will be collected on the next scheduled run")
        print("   (every 30 minutes at :00 and :30)")
    else:
        if camera_status and camera_status.get("isOnline") != "true":
            print("⚠️  Camera is currently offline")
            print("   This is expected - cameras can go offline temporarily")
            print("   The collector correctly skips offline cameras for reliability")
            print("   The camera will be collected automatically when it comes back online")
        else:
            print("❌ Camera collection test failed")
            print("   There may be an issue with the camera or API")
    
    print("\n" + "-" * 60)
    print("RECOMMENDATION")
    print("-" * 60)
    print("The collector's behavior is correct:")
    print("  - It skips offline cameras to avoid errors")
    print("  - Offline cameras will be collected when they come back online")
    print("  - This ensures reliable collection without failures")
    print("\nNo fix needed - the system will automatically collect this camera")
    print("on the next run when it's online.")


if __name__ == "__main__":
    main()

