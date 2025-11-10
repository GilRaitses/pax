#!/usr/bin/env python3
"""Compute preliminary stress scores from image features.

NOTE: This script requires torch and transformers. 
Either activate the venv: source venv/bin/activate
Or use the wrapper: scripts/2025-11-10/run_with_venv.sh scripts/2025-11-10/compute_stress_scores.py

Uses simple heuristics to compute stress scores:
- Pedestrian count (higher = more stress)
- Vehicle count (higher = more stress)
- Crowd density (higher = more stress)
- Visual complexity (higher = more stress)
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

from pax.vision.extractor import FeatureExtractor


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
    """Load image manifest and extract image paths."""
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)

    camera_images = {}
    for camera_id, camera_data in manifest.get("cameras", {}).items():
        camera_images[camera_id] = {
            "total_images": camera_data.get("total_images", 0),
            "images": camera_data.get("images", []),
        }

    return camera_images


def compute_stress_score(features: dict) -> float:
    """Compute stress score from extracted features using simple heuristics."""
    # Extract feature values
    yolo = features.get("yolo", {})
    detectron2 = features.get("detectron2", {})
    clip = features.get("clip", {})

    # Pedestrian count (weight: 0.3)
    pedestrian_count = (
        yolo.get("pedestrian_count", 0) + detectron2.get("pedestrian_count", 0)
    ) / 2.0
    pedestrian_score = min(pedestrian_count / 50.0, 1.0) * 0.3  # Normalize to 0-1, max 50 pedestrians

    # Vehicle count (weight: 0.25)
    vehicle_count = (
        yolo.get("vehicle_count", 0) + detectron2.get("vehicle_count", 0)
    ) / 2.0
    vehicle_score = min(vehicle_count / 30.0, 1.0) * 0.25  # Normalize to 0-1, max 30 vehicles

    # Crowd density (weight: 0.25)
    crowd_density = detectron2.get("crowd_density", 0.0)
    crowd_score = min(crowd_density, 1.0) * 0.25  # Already normalized 0-1

    # Visual complexity (weight: 0.2)
    # Use total detections as proxy for visual complexity
    total_detections = yolo.get("total_detections", 0) + detectron2.get("total_instances", 0)
    complexity_score = min(total_detections / 100.0, 1.0) * 0.2  # Normalize to 0-1, max 100 detections

    # Total stress score (0-1 scale)
    stress_score = pedestrian_score + vehicle_score + crowd_score + complexity_score

    return min(stress_score, 1.0)  # Cap at 1.0


def extract_features_for_images(
    image_paths: list[Path], extractor: FeatureExtractor, show_progress: bool = True
) -> list[dict]:
    """Extract features for a list of images."""
    results = []
    for image_path in image_paths:
        if not image_path.exists():
            print(f"WARNING: Image not found: {image_path}")
            continue

        try:
            features = extractor.extract(image_path)
            features["image_path"] = str(image_path)
            results.append(features)
        except Exception as e:
            print(f"WARNING: Failed to extract features from {image_path}: {e}")
            results.append(
                {
                    "image_path": str(image_path),
                    "yolo": {},
                    "detectron2": {},
                    "clip": {},
                    "errors": [str(e)],
                }
            )

    return results


def compute_stress_scores(
    camera_manifest_path: Path,
    image_manifest_path: Path,
    base_image_dir: Path | None = None,
    output_path: Path | None = None,
    use_extracted_features: bool = False,
    features_path: Path | None = None,
) -> dict:
    """Compute stress scores for all camera zones."""
    print("Loading camera manifest...")
    camera_map = load_camera_manifest(camera_manifest_path)
    print(f"Loaded {len(camera_map)} cameras")

    print("Loading image manifest...")
    image_data = load_image_manifest(image_manifest_path)
    print(f"Loaded image data for {len(image_data)} cameras")

    # Determine base image directory
    if base_image_dir is None:
        # Try common locations
        project_root = Path(__file__).parent.parent.parent
        possible_dirs = [
            project_root / "docs" / "backup" / "data_bkup" / "raw" / "images",
            project_root / "data" / "raw" / "images",
        ]
        for dir_path in possible_dirs:
            if dir_path.exists():
                base_image_dir = dir_path
                break

        if base_image_dir is None:
            print("ERROR: Could not find image directory. Please specify --base-image-dir")
            sys.exit(1)

    print(f"Using image directory: {base_image_dir}")

    # Load extracted features if available
    extracted_features = {}
    if use_extracted_features and features_path and features_path.exists():
        print(f"Loading extracted features from {features_path}...")
        with open(features_path) as f:
            features_data = json.load(f)
            # Index by image path
            for feature_dict in features_data:
                img_path = feature_dict.get("image_path", "")
                extracted_features[img_path] = feature_dict
        print(f"Loaded features for {len(extracted_features)} images")

    # Initialize extractor if needed
    extractor = None
    if not use_extracted_features or len(extracted_features) == 0:
        print("Initializing feature extractor...")
        extractor = FeatureExtractor()

    # Process each camera
    camera_stress_scores = {}
    zone_stress_scores = defaultdict(list)

    for camera_id, camera_info in camera_map.items():
        camera_number = camera_info["number"]
        images_info = image_data.get(camera_id, {}).get("images", [])

        if not images_info:
            continue

        # Collect image paths
        image_paths = []
        for img_info in images_info:
            local_path = img_info.get("local_path", "")
            if local_path:
                # Try relative to base_image_dir's parent (since local_path starts with "images/")
                # e.g., base_image_dir = docs/backup/data_bkup/raw/images
                # local_path = images/2025-11-05/...
                # full_path should be docs/backup/data_bkup/raw/images/2025-11-05/...
                if base_image_dir:
                    # Remove "images/" prefix if present
                    if local_path.startswith("images/"):
                        rel_path = local_path[7:]  # Remove "images/" prefix
                        full_path = base_image_dir / rel_path
                    else:
                        full_path = base_image_dir.parent / local_path
                else:
                    full_path = Path(local_path)
                
                if not full_path.exists():
                    # Try as absolute path
                    full_path = Path(local_path)
                
                if full_path.exists():
                    image_paths.append(full_path)

        if not image_paths:
            continue

        # Extract features or use pre-extracted
        features_list = []
        if use_extracted_features and extracted_features:
            for img_path in image_paths:
                # Try to find matching feature
                for feat_path, feat_data in extracted_features.items():
                    if str(img_path) in feat_path or feat_path in str(img_path):
                        features_list.append(feat_data)
                        break
        else:
            print(f"Extracting features for camera {camera_number} ({camera_id})...")
            features_list = extract_features_for_images(image_paths, extractor, show_progress=False)

        # Compute stress scores for each image
        stress_scores = []
        for features in features_list:
            if features.get("errors"):
                continue  # Skip images with extraction errors
            stress_score = compute_stress_score(features)
            stress_scores.append(stress_score)

        if stress_scores:
            mean_stress = sum(stress_scores) / len(stress_scores)
            camera_stress_scores[camera_id] = {
                "camera_id": camera_id,
                "camera_number": camera_number,
                "camera_name": camera_info["name"],
                "mean_stress": mean_stress,
                "image_count": len(stress_scores),
                "stress_scores": stress_scores,
            }
            zone_stress_scores[camera_number].append(mean_stress)

    # Compute zone-level stress scores
    zone_means = {}
    for zone_number, scores in zone_stress_scores.items():
        zone_means[zone_number] = sum(scores) / len(scores) if scores else 0.0

    # Generate output
    output = {
        "metadata": {
            "total_cameras": len(camera_stress_scores),
            "total_zones": len(zone_means),
            "computation_method": "heuristic",
            "weights": {
                "pedestrian_count": 0.3,
                "vehicle_count": 0.25,
                "crowd_density": 0.25,
                "visual_complexity": 0.2,
            },
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
    print("STRESS SCORES SUMMARY")
    print("=" * 60)
    print(f"Total cameras with scores: {len(camera_stress_scores)}")
    print(f"Total zones with scores: {len(zone_means)}")
    if zone_means:
        mean_stress = sum(zone_means.values()) / len(zone_means)
        print(f"Mean stress across zones: {mean_stress:.3f}")
        print(f"Min stress: {min(zone_means.values()):.3f}")
        print(f"Max stress: {max(zone_means.values()):.3f}")

    return output


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Compute preliminary stress scores")
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
        "--base-image-dir",
        type=Path,
        help="Base directory for images (auto-detected if not provided)",
    )
    parser.add_argument(
        "--use-extracted-features",
        action="store_true",
        help="Use pre-extracted features instead of extracting on-the-fly",
    )
    parser.add_argument(
        "--features-path",
        type=Path,
        help="Path to extracted features JSON file (required if --use-extracted-features)",
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

    if args.use_extracted_features and not args.features_path:
        print("ERROR: --features-path required when using --use-extracted-features")
        sys.exit(1)

    compute_stress_scores(
        args.camera_manifest,
        args.image_manifest,
        args.base_image_dir,
        args.output,
        args.use_extracted_features,
        args.features_path,
    )


if __name__ == "__main__":
    main()

