#!/usr/bin/env python3
"""Extract features from all collected images.

This script processes all images and stores features in a structured format (JSON or Parquet).
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pax.vision.extractor import FeatureExtractor


def find_all_images(base_dir: Path) -> list[Path]:
    """Find all JPG images in the directory tree."""
    images = []
    if base_dir.exists():
        images.extend(base_dir.rglob("*.jpg"))
        images.extend(base_dir.rglob("*.jpeg"))
    return sorted(images)


def extract_features_batch(
    image_paths: list[Path],
    output_format: str = "json",
    output_dir: Path | None = None,
    show_progress: bool = True,
) -> dict:
    """Extract features from all images and save results."""
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "data" / "processed" / "features"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Found {len(image_paths)} images to process")
    print(f"Output directory: {output_dir}")
    print("=" * 60)

    # Initialize extractor
    print("Initializing feature extractor...")
    extractor = FeatureExtractor()

    # Extract features
    print("Extracting features...")
    results = extractor.extract_batch(image_paths, show_progress=show_progress)

    # Generate timestamp for output files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save results
    if output_format == "json":
        output_file = output_dir / f"features_{timestamp}.json"
        with output_file.open("w") as f:
            json.dump(results, f, indent=2)
        print(f"\nFeatures saved to: {output_file}")
    elif output_format == "parquet":
        # Flatten results for Parquet
        flattened = []
        for result in results:
            flat = {
                "image_path": result["image_path"],
                "yolo_pedestrians": result.get("yolo", {}).get("pedestrian_count", 0),
                "yolo_vehicles": result.get("yolo", {}).get("vehicle_count", 0),
                "yolo_bikes": result.get("yolo", {}).get("bike_count", 0),
                "yolo_total": result.get("yolo", {}).get("total_detections", 0),
                "d2_pedestrians": result.get("detectron2", {}).get("pedestrian_count", 0),
                "d2_vehicles": result.get("detectron2", {}).get("vehicle_count", 0),
                "d2_bikes": result.get("detectron2", {}).get("bike_count", 0),
                "d2_crowd_density": result.get("detectron2", {}).get("crowd_density", 0.0),
                "d2_area_covered": result.get("detectron2", {}).get("total_area_covered", 0.0),
                "d2_total": result.get("detectron2", {}).get("total_instances", 0),
                "clip_top_scene": result.get("clip", {}).get("top_scene", ""),
                "clip_confidence": result.get("clip", {}).get("top_confidence", 0.0),
                "has_errors": len(result.get("errors", [])) > 0,
                "error_count": len(result.get("errors", [])),
            }
            flattened.append(flat)

        df = pd.DataFrame(flattened)
        output_file = output_dir / f"features_{timestamp}.parquet"
        df.to_parquet(output_file, index=False)
        print(f"\nFeatures saved to: {output_file}")
        print(f"Total rows: {len(df)}")
    else:
        # Save both formats
        json_file = output_dir / f"features_{timestamp}.json"
        with json_file.open("w") as f:
            json.dump(results, f, indent=2)

        flattened = []
        for result in results:
            flat = {
                "image_path": result["image_path"],
                "yolo_pedestrians": result.get("yolo", {}).get("pedestrian_count", 0),
                "yolo_vehicles": result.get("yolo", {}).get("vehicle_count", 0),
                "yolo_bikes": result.get("yolo", {}).get("bike_count", 0),
                "yolo_total": result.get("yolo", {}).get("total_detections", 0),
                "d2_pedestrians": result.get("detectron2", {}).get("pedestrian_count", 0),
                "d2_vehicles": result.get("detectron2", {}).get("vehicle_count", 0),
                "d2_bikes": result.get("detectron2", {}).get("bike_count", 0),
                "d2_crowd_density": result.get("detectron2", {}).get("crowd_density", 0.0),
                "d2_area_covered": result.get("detectron2", {}).get("total_area_covered", 0.0),
                "d2_total": result.get("detectron2", {}).get("total_instances", 0),
                "clip_top_scene": result.get("clip", {}).get("top_scene", ""),
                "clip_confidence": result.get("clip", {}).get("top_confidence", 0.0),
                "has_errors": len(result.get("errors", [])) > 0,
                "error_count": len(result.get("errors", [])),
            }
            flattened.append(flat)

        df = pd.DataFrame(flattened)
        parquet_file = output_dir / f"features_{timestamp}.parquet"
        df.to_parquet(parquet_file, index=False)
        print(f"\nFeatures saved to:")
        print(f"  JSON: {json_file}")
        print(f"  Parquet: {parquet_file}")
        print(f"  Total rows: {len(df)}")

    # Generate summary report
    successful = sum(1 for r in results if not r.get("errors"))
    failed = len(results) - successful

    summary = {
        "timestamp": timestamp,
        "total_images": len(results),
        "successful": successful,
        "failed": failed,
        "output_file": str(output_file) if output_format != "both" else str(parquet_file),
        "summary_stats": {
            "avg_yolo_pedestrians": sum(
                r.get("yolo", {}).get("pedestrian_count", 0) for r in results
            )
            / len(results)
            if results
            else 0,
            "avg_yolo_vehicles": sum(
                r.get("yolo", {}).get("vehicle_count", 0) for r in results
            )
            / len(results)
            if results
            else 0,
            "avg_d2_crowd_density": sum(
                r.get("detectron2", {}).get("crowd_density", 0.0) for r in results
            )
            / len(results)
            if results
            else 0,
        },
    }

    report_file = output_dir / f"extraction_report_{timestamp}.json"
    with report_file.open("w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nExtraction report: {report_file}")
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total images processed: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Average pedestrians (YOLO): {summary['summary_stats']['avg_yolo_pedestrians']:.1f}")
    print(f"Average vehicles (YOLO): {summary['summary_stats']['avg_yolo_vehicles']:.1f}")
    print(f"Average crowd density (Detectron2): {summary['summary_stats']['avg_d2_crowd_density']:.2f}")

    return summary


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Extract features from all collected images")
    parser.add_argument(
        "--input-dir",
        type=Path,
        help="Directory containing images (default: auto-detect)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory for features (default: data/processed/features)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "parquet", "both"],
        default="both",
        help="Output format (default: both)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of images to process (for testing)",
    )

    args = parser.parse_args()

    # Find images
    if args.input_dir:
        image_dirs = [args.input_dir]
    else:
        # Auto-detect: check both data/raw/images and backup location
        project_root = Path(__file__).parent.parent
        image_dirs = [
            project_root / "data" / "raw" / "images",
            project_root / "docs" / "backup" / "data_bkup" / "raw" / "images",
        ]

    all_images = []
    for img_dir in image_dirs:
        images = find_all_images(img_dir)
        all_images.extend(images)
        if images:
            print(f"Found {len(images)} images in {img_dir}")

    if not all_images:
        print("ERROR: No images found!")
        sys.exit(1)

    # Remove duplicates
    all_images = list(set(all_images))
    all_images.sort()

    if args.limit:
        all_images = all_images[: args.limit]
        print(f"Limiting to {args.limit} images")

    # Extract features
    extract_features_batch(
        all_images,
        output_format=args.format,
        output_dir=args.output_dir,
        show_progress=True,
    )


if __name__ == "__main__":
    main()

