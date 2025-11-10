#!/usr/bin/env python3
"""Test script for CLIP wrapper."""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pax.vision.clip import CLIPWrapper


def main():
    """Test CLIP wrapper on sample images."""
    # Find sample images
    backup_dir = Path(__file__).parent.parent / "docs" / "backup" / "data_bkup" / "raw" / "images"
    
    if not backup_dir.exists():
        print(f"Backup directory not found: {backup_dir}")
        return
    
    # Find first few images
    image_paths = list(backup_dir.rglob("*.jpg"))[:3]
    
    if not image_paths:
        print(f"No images found in {backup_dir}")
        return
    
    print(f"Found {len(image_paths)} sample images")
    print("=" * 60)
    
    # Initialize wrapper
    print("Initializing CLIP wrapper...")
    try:
        wrapper = CLIPWrapper()
    except Exception as e:
        print(f"ERROR: Failed to initialize wrapper: {e}")
        return
    
    # Test on each image
    results = []
    for i, image_path in enumerate(image_paths, 1):
        print(f"\n[{i}/{len(image_paths)}] Processing: {image_path.name}")
        print("-" * 60)
        
        try:
            result = wrapper.understand_scene(image_path)
            results.append({
                "image_path": str(image_path),
                "image_name": image_path.name,
                **result
            })
            
            print(f"  Top scene: {result['top_scene']}")
            print(f"  Confidence: {result['top_confidence']:.2%}")
            print(f"  Top 3 scenes:")
            for label_info in result['scene_labels'][:3]:
                print(f"    - {label_info['label']}: {label_info['score']:.2%}")
            print(f"  Feature vector size: {len(result['semantic_features'])}")
            
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
    
    scenes = [r.get("top_scene") for r in results if r.get("top_scene")]
    from collections import Counter
    scene_counts = Counter(scenes)
    
    print("Scene distribution:")
    for scene, count in scene_counts.most_common():
        print(f"  {scene}: {count}")
    
    # Save results
    output_file = Path(__file__).parent / "clip_test_results.json"
    with output_file.open("w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")
    print("Test completed!")


if __name__ == "__main__":
    main()

