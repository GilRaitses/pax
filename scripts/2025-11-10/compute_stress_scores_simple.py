#!/usr/bin/env python3
"""Compute preliminary stress scores using simple heuristics (no feature extraction).

This is a simplified version that uses image counts and metadata as proxies for stress scores.
Use this when feature extraction is not available or for quick testing.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def load_camera_manifest(manifest_path: Path) -> dict[str, dict]:
    """Load camera manifest and create mapping from camera_id to camera number."""
    with open(manifest_path) as f:
        manifest = json.load(f)

    camera_map = {}
    for camera in manifest.get("cameras", []):
        camera_id = camera.get("id")
        camera_number = camera.get("number")
        if camera_id and camera_number:
            camera_map[camera_id] = {
                "number": camera_number,
                "name": camera.get("name", ""),
            }

    return camera_map


def load_image_manifest(manifest_path: Path) -> dict[str, dict]:
    """Load image manifest and extract image counts per camera."""
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)

    camera_images = {}
    for camera_id, camera_data in manifest.get("cameras", {}).items():
        camera_images[camera_id] = {
            "total_images": camera_data.get("total_images", 0),
            "images": camera_data.get("images", []),
            "images_by_date": camera_data.get("images_by_date", {}),
        }

    return camera_images


def compute_stress_score_simple(image_count: int, time_span_days: float = 1.0) -> float:
    """Compute stress score using simple heuristics based on image count.
    
    This is a placeholder that uses image count as a proxy for activity/stress.
    Higher image count = more activity = potentially higher stress.
    """
    # Normalize image count to 0-1 scale
    # Assume 2 images per day is baseline (low stress)
    # Scale up to 1.0 for higher counts
    baseline_images = 2.0 * time_span_days
    if baseline_images == 0:
        baseline_images = 1.0
    
    # Simple linear scaling: more images = higher stress (up to a max)
    normalized = min(image_count / (baseline_images * 2), 1.0)
    
    # Add some randomness/variation based on camera number (for visualization)
    # This is just for demonstration - real scores would come from feature extraction
    stress_score = normalized * 0.5 + 0.1  # Range: 0.1 to 0.6
    
    return stress_score


def compute_stress_scores_simple(
    camera_manifest_path: Path,
    image_manifest_path: Path,
    output_path: Path | None = None,
) -> dict:
    """Compute stress scores using simple heuristics."""
    print("Loading camera manifest...")
    camera_map = load_camera_manifest(camera_manifest_path)
    print(f"Loaded {len(camera_map)} cameras")

    print("Loading image manifest...")
    image_data = load_image_manifest(image_manifest_path)
    print(f"Loaded image data for {len(image_data)} cameras")

    # Process each camera
    camera_stress_scores = {}
    zone_stress_scores = defaultdict(list)

    for camera_id, camera_info in camera_map.items():
        camera_number = camera_info["number"]
        images_info = image_data.get(camera_id, {})
        image_count = images_info.get("total_images", 0)
        images_by_date = images_info.get("images_by_date", {})

        if image_count == 0:
            continue

        # Estimate time span
        time_span_days = len(images_by_date) if images_by_date else 1.0

        # Compute simple stress score
        stress_score = compute_stress_score_simple(image_count, time_span_days)

        camera_stress_scores[camera_id] = {
            "camera_id": camera_id,
            "camera_number": camera_number,
            "camera_name": camera_info["name"],
            "mean_stress": stress_score,
            "image_count": image_count,
            "method": "simple_heuristic",
        }
        zone_stress_scores[camera_number].append(stress_score)

    # Compute zone-level stress scores
    zone_means = {}
    for zone_number, scores in zone_stress_scores.items():
        zone_means[zone_number] = sum(scores) / len(scores) if scores else 0.0

    # Generate output
    output = {
        "metadata": {
            "total_cameras": len(camera_stress_scores),
            "total_zones": len(zone_means),
            "computation_method": "simple_heuristic",
            "note": "These are placeholder scores based on image counts. Use compute_stress_scores.py with feature extraction for actual stress scores.",
        },
        "camera_stress": camera_stress_scores,
        "zone_stress": {
            zone_num: {
                "mean_stress": stress,
                "camera_count": len(zone_stress_scores[zone_num]),
            }
            for zone_num, stress in sorted(zone_means.items())
        },
    }

    # Save output
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)
        print(f"\nStress scores saved to: {output_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("STRESS SCORES SUMMARY (Simple Heuristic)")
    print("=" * 60)
    print(f"Total cameras with scores: {len(camera_stress_scores)}")
    print(f"Total zones with scores: {len(zone_means)}")
    if zone_means:
        mean_stress = sum(zone_means.values()) / len(zone_means)
        print(f"Mean stress across zones: {mean_stress:.3f}")
        print(f"Min stress: {min(zone_means.values()):.3f}")
        print(f"Max stress: {max(zone_means.values()):.3f}")
    print("\nNOTE: These are placeholder scores. Run compute_stress_scores.py")
    print("      with feature extraction for actual stress scores.")

    return output


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Compute preliminary stress scores (simple heuristic)")
    parser.add_argument(
        "--camera-manifest",
        type=Path,
        default=Path("data/manifests/corridor_cameras_numbered.json"),
        help="Path to camera manifest (default: data/manifests/corridor_cameras_numbered.json)",
    )
    parser.add_argument(
        "--image-manifest",
        type=Path,
        default=Path("data/manifests/image_manifest.yaml"),
        help="Path to image manifest (default: data/manifests/image_manifest.yaml)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/stress_scores_preliminary.json"),
        help="Output path for stress scores (default: data/stress_scores_preliminary.json)",
    )

    args = parser.parse_args()

    if not args.camera_manifest.exists():
        print(f"ERROR: Camera manifest not found: {args.camera_manifest}")
        sys.exit(1)

    if not args.image_manifest.exists():
        print(f"ERROR: Image manifest not found: {args.image_manifest}")
        sys.exit(1)

    compute_stress_scores_simple(args.camera_manifest, args.image_manifest, args.output)


if __name__ == "__main__":
    main()

