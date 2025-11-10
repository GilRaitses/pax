#!/usr/bin/env python3
"""Test script for unified feature extractor."""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pax.vision.extractor import FeatureExtractor


def main():
    """Test unified feature extractor on sample images."""
    # Find sample images
    backup_dir = Path(__file__).parent.parent / "docs" / "backup" / "data_bkup" / "raw" / "images"
    
    if not backup_dir.exists():
        print(f"Backup directory not found: {backup_dir}")
        return
    
    # Find first 2 images for quick test
    image_paths = list(backup_dir.rglob("*.jpg"))[:2]
    
    if not image_paths:
        print(f"No images found in {backup_dir}")
        return
    
    print(f"Testing unified feature extractor on {len(image_paths)} images")
    print("=" * 60)
    
    # Initialize extractor
    print("Initializing feature extractor...")
    try:
        extractor = FeatureExtractor()
    except Exception as e:
        print(f"ERROR: Failed to initialize extractor: {e}")
        return
    
    # Extract features
    results = []
    for i, image_path in enumerate(image_paths, 1):
        print(f"\n[{i}/{len(image_paths)}] Extracting from: {image_path.name}")
        print("-" * 60)
        
        try:
            result = extractor.extract(image_path)
            results.append(result)
            
            # Print summary
            if result.get("yolo"):
                yolo = result["yolo"]
                print(f"  YOLOv8n: {yolo.get('pedestrian_count', 0)} pedestrians, "
                      f"{yolo.get('vehicle_count', 0)} vehicles, "
                      f"{yolo.get('bike_count', 0)} bikes")
            
            if result.get("detectron2"):
                d2 = result["detectron2"]
                print(f"  Detectron2: {d2.get('pedestrian_count', 0)} pedestrians, "
                      f"crowd density: {d2.get('crowd_density', 0):.2f}")
            
            if result.get("clip"):
                clip = result["clip"]
                print(f"  CLIP: {clip.get('top_scene', 'N/A')} "
                      f"({clip.get('top_confidence', 0):.1%})")
            
            if result.get("errors"):
                print(f"  Errors: {result['errors']}")
                
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({
                "image_path": str(image_path),
                "errors": [str(e)]
            })
    
    # Save results
    output_file = Path(__file__).parent / "extractor_test_results.json"
    with output_file.open("w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")
    print("Test completed!")


if __name__ == "__main__":
    main()

