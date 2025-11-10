#!/usr/bin/env python3
"""Test script for YOLOv8n wrapper."""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pax.vision.yolov8n import YOLOv8nDetector


def main():
    """Test YOLOv8n detector on sample images."""
    # Find sample images
    backup_dir = Path(__file__).parent.parent / "docs" / "backup" / "data_bkup" / "raw" / "images"
    
    if not backup_dir.exists():
        print(f"Backup directory not found: {backup_dir}")
        return
    
    # Find first few images
    image_paths = list(backup_dir.rglob("*.jpg"))[:5]
    
    if not image_paths:
        print(f"No images found in {backup_dir}")
        return
    
    print(f"Found {len(image_paths)} sample images")
    print("=" * 60)
    
    # Initialize detector
    print("Initializing YOLOv8n detector...")
    detector = YOLOv8nDetector()
    
    # Test on each image
    results = []
    for i, image_path in enumerate(image_paths, 1):
        print(f"\n[{i}/{len(image_paths)}] Processing: {image_path.name}")
        print("-" * 60)
        
        try:
            result = detector.detect(image_path)
            results.append({
                "image_path": str(image_path),
                "image_name": image_path.name,
                **result
            })
            
            print(f"  Pedestrians: {result['pedestrian_count']}")
            print(f"  Vehicles:    {result['vehicle_count']}")
            print(f"  Bikes:       {result['bike_count']}")
            print(f"  Total detections: {result['total_detections']}")
            
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({
                "image_path": str(image_path),
                "image_name": image_path.name,
                "error": str(e)
            })
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    total_pedestrians = sum(r.get("pedestrian_count", 0) for r in results)
    total_vehicles = sum(r.get("vehicle_count", 0) for r in results)
    total_bikes = sum(r.get("bike_count", 0) for r in results)
    
    print(f"Total pedestrians detected: {total_pedestrians}")
    print(f"Total vehicles detected:    {total_vehicles}")
    print(f"Total bikes detected:       {total_bikes}")
    
    # Save results
    output_file = Path(__file__).parent / "yolov8n_test_results.json"
    with output_file.open("w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")
    print("Test completed successfully!")


if __name__ == "__main__":
    main()

