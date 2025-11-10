#!/usr/bin/env python3
"""Test script: Collect from a single camera multiple times per minute to verify Cloud Run execution."""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

def load_manifest(manifest_path: Path) -> dict:
    """Load camera manifest."""
    with open(manifest_path) as f:
        if manifest_path.suffix == '.yaml':
            import yaml
            return yaml.safe_load(f)
        else:
            return json.load(f)

def test_single_camera_collection(
    manifest_path: Path,
    camera_index: int = 0,
    interval_seconds: int = 10,
    duration_minutes: int = 1,
    project: str = "pax-nyc",
    region: str = "us-central1",
    job_name: str = "pax-collector"
) -> dict:
    """Test collecting from a single camera multiple times."""
    
    print("=" * 60)
    print("SINGLE CAMERA COLLECTION TEST")
    print("=" * 60)
    print()
    
    # Load manifest
    print(f"Loading manifest: {manifest_path}")
    manifest = load_manifest(manifest_path)
    cameras = manifest.get('cameras', [])
    
    if not cameras:
        print("❌ No cameras found in manifest", file=sys.stderr)
        sys.exit(1)
    
    test_camera = cameras[camera_index]
    print(f"Test Camera: #{test_camera.get('number', 'N/A')} - {test_camera.get('name', 'Unknown')}")
    print(f"Interval: {interval_seconds} seconds")
    print(f"Duration: {duration_minutes} minute(s)")
    print(f"Expected Collections: {duration_minutes * 60 // interval_seconds}")
    print()
    
    # Create temporary manifest with just this camera
    temp_manifest = {
        'cameras': [test_camera],
        'metadata': manifest.get('metadata', {})
    }
    temp_manifest_path = Path('/tmp/test_single_camera_manifest.json')
    with open(temp_manifest_path, 'w') as f:
        json.dump(temp_manifest, f, indent=2)
    
    print(f"Created temporary manifest: {temp_manifest_path}")
    print()
    
    # Test results
    results = {
        'camera': test_camera,
        'start_time': datetime.now(ZoneInfo("America/New_York")).isoformat(),
        'collections': [],
        'success_count': 0,
        'failure_count': 0
    }
    
    # Run collections
    num_collections = duration_minutes * 60 // interval_seconds
    print(f"Starting {num_collections} collections...")
    print()
    
    for i in range(num_collections):
        collection_num = i + 1
        print(f"Collection {collection_num}/{num_collections}...", end=' ', flush=True)
        
        start_time = datetime.now(ZoneInfo("America/New_York"))
        
        # Execute Cloud Run job
        result = subprocess.run(
            ['gcloud', 'run', 'jobs', 'execute', job_name,
             '--region', region,
             '--project', project,
             '--update-env-vars', f'PAX_CAMERA_MANIFEST={temp_manifest_path}',
             '--format', 'json'],
            capture_output=True,
            text=True
        )
        
        end_time = datetime.now(ZoneInfo("America/New_York"))
        duration = (end_time - start_time).total_seconds()
        
        collection_result = {
            'collection_num': collection_num,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration_seconds': duration,
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
        
        if result.returncode == 0:
            print("✅ SUCCESS")
            results['success_count'] += 1
        else:
            print("❌ FAILED")
            print(f"   Error: {result.stderr[:200]}")
            results['failure_count'] += 1
        
        results['collections'].append(collection_result)
        
        # Wait before next collection (except for last one)
        if i < num_collections - 1:
            time.sleep(interval_seconds)
    
    results['end_time'] = datetime.now(ZoneInfo("America/New_York")).isoformat()
    
    # Summary
    print()
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total Collections: {num_collections}")
    print(f"Successful: {results['success_count']}")
    print(f"Failed: {results['failure_count']}")
    print(f"Success Rate: {results['success_count'] / num_collections * 100:.1f}%")
    print()
    
    if results['success_count'] == num_collections:
        print("✅ ALL COLLECTIONS SUCCEEDED - Cloud Run execution works!")
    elif results['success_count'] > 0:
        print("⚠️  PARTIAL SUCCESS - Some collections failed")
    else:
        print("❌ ALL COLLECTIONS FAILED - Cloud Run execution has issues")
    
    return results

def main() -> int:
    parser = argparse.ArgumentParser(description="Test single camera collection")
    parser.add_argument('--manifest', type=Path, 
                       default=Path('data/manifests/corridor_cameras_numbered.json'),
                       help='Camera manifest path')
    parser.add_argument('--camera-index', type=int, default=0,
                       help='Camera index to test (default: 0)')
    parser.add_argument('--interval', type=int, default=10,
                       help='Interval between collections in seconds (default: 10)')
    parser.add_argument('--duration', type=int, default=1,
                       help='Test duration in minutes (default: 1)')
    parser.add_argument('--project', default='pax-nyc', help='GCP project')
    parser.add_argument('--region', default='us-central1', help='GCP region')
    parser.add_argument('--job', default='pax-collector', help='Cloud Run job name')
    parser.add_argument('--output', type=Path, help='Output JSON file for results')
    
    args = parser.parse_args()
    
    if not args.manifest.exists():
        print(f"❌ Manifest not found: {args.manifest}", file=sys.stderr)
        return 1
    
    try:
        results = test_single_camera_collection(
            manifest_path=args.manifest,
            camera_index=args.camera_index,
            interval_seconds=args.interval,
            duration_minutes=args.duration,
            project=args.project,
            region=args.region,
            job_name=args.job
        )
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\nResults saved to: {args.output}")
        
        return 0 if results['success_count'] == len(results['collections']) else 1
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())

