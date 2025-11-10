#!/usr/bin/env python3
"""Enhanced batch image processing with parallelization, retry logic, and checkpointing.

This script processes images in parallel, handles failures gracefully with retry logic,
and can resume from a checkpoint if interrupted.
"""

import argparse
import json
import logging
import multiprocessing
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from tqdm import tqdm

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from pax.vision.extractor import FeatureExtractor

LOGGER = logging.getLogger(__name__)


def extract_camera_id_from_path(image_path: Path) -> str | None:
    """Extract camera ID from image path.

    Supports formats:
    - YYYY-MM-DD/camera-id_timestamp.jpg
    - images/camera-id/timestamp.jpg
    - camera-id_timestamp.jpg
    """
    parts = image_path.parts
    filename = image_path.stem  # Without extension

    # Try format: YYYY-MM-DD/camera-id_timestamp.jpg
    if len(parts) >= 2:
        # Check if filename contains underscore (camera-id_timestamp)
        if "_" in filename:
            camera_id = filename.split("_")[0]
            return camera_id

    # Try format: images/camera-id/timestamp.jpg
    if "images" in parts:
        idx = parts.index("images")
        if idx + 1 < len(parts):
            return parts[idx + 1]

    # Try parent directory as camera ID
    if len(parts) >= 2:
        parent = parts[-2]
        # Skip date directories (YYYY-MM-DD format)
        if not parent.replace("-", "").isdigit():
            return parent

    return None


def extract_timestamp_from_path(image_path: Path) -> datetime | None:
    """Extract timestamp from image path or filename."""
    filename = image_path.stem

    # Try format: camera-id_YYYYMMDDTHHMMSS
    if "_" in filename:
        timestamp_str = filename.split("_", 1)[1]
        try:
            return datetime.strptime(timestamp_str, "%Y%m%dT%H%M%S")
        except ValueError:
            pass

    # Try format: YYYYMMDDTHHMMSS
    try:
        return datetime.strptime(filename, "%Y%m%dT%H%M%S")
    except ValueError:
        pass

    # Fallback: use file modification time
    try:
        return datetime.fromtimestamp(image_path.stat().st_mtime)
    except OSError:
        return None


def process_single_image(
    image_path: Path,
    extractor: FeatureExtractor | None = None,
    max_retries: int = 3,
    retry_delay: float = 1.0,
) -> dict[str, Any]:
    """Process a single image with retry logic.

    Args:
        image_path: Path to the image file.
        extractor: FeatureExtractor instance (will be created if None).
        max_retries: Maximum number of retry attempts.
        retry_delay: Delay between retries in seconds.

    Returns:
        Dictionary with extraction result or error information.
    """
    if extractor is None:
        extractor = FeatureExtractor()

    camera_id = extract_camera_id_from_path(image_path)
    timestamp = extract_timestamp_from_path(image_path)

    result = {
        "image_path": str(image_path),
        "camera_id": camera_id,
        "timestamp": timestamp.isoformat() if timestamp else None,
        "yolo": {},
        "detectron2": {},
        "clip": {},
        "errors": [],
        "retry_count": 0,
        "success": False,
    }

    for attempt in range(max_retries):
        try:
            features = extractor.extract(image_path)
            result.update(features)
            result["success"] = len(features.get("errors", [])) == 0
            result["retry_count"] = attempt
            return result
        except Exception as e:
            result["retry_count"] = attempt + 1
            error_msg = f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}"
            result["errors"].append(error_msg)
            LOGGER.warning("Failed to extract features from %s: %s", image_path, e)

            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
            else:
                result["success"] = False
                return result

    return result


def process_worker(args: tuple[Path, int, float]) -> dict[str, Any]:
    """Worker function for parallel processing.

    Args:
        args: Tuple of (image_path, max_retries, retry_delay).

    Returns:
        Extraction result dictionary.
    """
    image_path, max_retries, retry_delay = args
    return process_single_image(image_path, max_retries=max_retries, retry_delay=retry_delay)


def load_checkpoint(checkpoint_file: Path) -> set[str]:
    """Load processed image paths from checkpoint file.

    Args:
        checkpoint_file: Path to checkpoint JSON file.

    Returns:
        Set of processed image paths (as strings).
    """
    if not checkpoint_file.exists():
        return set()

    try:
        with checkpoint_file.open("r") as f:
            checkpoint_data = json.load(f)
            return set(checkpoint_data.get("processed_images", []))
    except Exception as e:
        LOGGER.warning("Failed to load checkpoint: %s", e)
        return set()


def save_checkpoint(checkpoint_file: Path, processed_images: set[str], stats: dict[str, Any]) -> None:
    """Save checkpoint with processed image paths and statistics.

    Args:
        checkpoint_file: Path to checkpoint JSON file.
        processed_images: Set of processed image paths.
        stats: Statistics dictionary to save.
    """
    checkpoint_data = {
        "processed_images": list(processed_images),
        "stats": stats,
        "last_updated": datetime.now().isoformat(),
    }

    try:
        with checkpoint_file.open("w") as f:
            json.dump(checkpoint_data, f, indent=2)
    except Exception as e:
        LOGGER.error("Failed to save checkpoint: %s", e)


def find_all_images(base_dir: Path) -> list[Path]:
    """Find all JPG images in the directory tree."""
    images = []
    if base_dir.exists():
        images.extend(base_dir.rglob("*.jpg"))
        images.extend(base_dir.rglob("*.jpeg"))
    return sorted(images)


def process_images_batch(
    image_paths: list[Path],
    output_dir: Path,
    output_format: str = "both",
    num_workers: int | None = None,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    checkpoint_file: Path | None = None,
    checkpoint_interval: int = 10,
    show_progress: bool = True,
) -> dict[str, Any]:
    """Process images in parallel with checkpointing and retry logic.

    Args:
        image_paths: List of image paths to process.
        output_dir: Output directory for features.
        output_format: Output format ("json", "parquet", or "both").
        num_workers: Number of parallel workers (default: CPU count).
        max_retries: Maximum retry attempts per image.
        retry_delay: Delay between retries in seconds.
        checkpoint_file: Path to checkpoint file for resuming.
        checkpoint_interval: Save checkpoint every N images.
        show_progress: Whether to show progress bar.

    Returns:
        Summary dictionary with processing statistics.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load checkpoint if resuming
    processed_images = set()
    if checkpoint_file:
        processed_images = load_checkpoint(checkpoint_file)
        LOGGER.info("Loaded checkpoint: %d images already processed", len(processed_images))

    # Filter out already processed images
    remaining_images = [
        img for img in image_paths if str(img) not in processed_images
    ]

    if not remaining_images:
        LOGGER.info("All images already processed!")
        return {"status": "complete", "message": "All images were already processed"}

    LOGGER.info("Processing %d images (%d already processed)", len(remaining_images), len(processed_images))

    # Set up parallel processing
    if num_workers is None:
        num_workers = multiprocessing.cpu_count()

    # Prepare worker arguments
    worker_args = [
        (img_path, max_retries, retry_delay) for img_path in remaining_images
    ]

    # Process images in parallel
    results = []
    processed_count = 0

    with multiprocessing.Pool(processes=num_workers) as pool:
        if show_progress:
            iterator = tqdm(
                pool.imap(process_worker, worker_args),
                total=len(remaining_images),
                desc="Extracting features",
            )
        else:
            iterator = pool.imap(process_worker, worker_args)

        for result in iterator:
            results.append(result)
            processed_count += 1

            # Save checkpoint periodically
            if checkpoint_file and processed_count % checkpoint_interval == 0:
                processed_images.add(result["image_path"])
                stats = {
                    "total_processed": len(processed_images),
                    "successful": sum(1 for r in results if r.get("success", False)),
                    "failed": sum(1 for r in results if not r.get("success", False)),
                }
                save_checkpoint(checkpoint_file, processed_images, stats)

    # Final checkpoint save
    if checkpoint_file:
        for result in results:
            processed_images.add(result["image_path"])
        stats = {
            "total_processed": len(processed_images),
            "successful": sum(1 for r in results if r.get("success", False)),
            "failed": sum(1 for r in results if not r.get("success", False)),
        }
        save_checkpoint(checkpoint_file, processed_images, stats)

    # Generate timestamp for output files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save results
    successful = sum(1 for r in results if r.get("success", False))
    failed = len(results) - successful

    if output_format in {"json", "both"}:
        json_file = output_dir / f"features_{timestamp}.json"
        with json_file.open("w") as f:
            json.dump(results, f, indent=2)
        LOGGER.info("Saved JSON features to: %s", json_file)

    if output_format in {"parquet", "both"}:
        # Flatten results for Parquet
        flattened = []
        for result in results:
            flat = {
                "image_path": result["image_path"],
                "camera_id": result.get("camera_id"),
                "timestamp": result.get("timestamp"),
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
                "retry_count": result.get("retry_count", 0),
                "success": result.get("success", False),
            }
            flattened.append(flat)

        df = pd.DataFrame(flattened)
        parquet_file = output_dir / f"features_{timestamp}.parquet"
        df.to_parquet(parquet_file, index=False)
        LOGGER.info("Saved Parquet features to: %s (%d rows)", parquet_file, len(df))

    # Generate summary report
    summary = {
        "timestamp": timestamp,
        "total_images": len(results),
        "successful": successful,
        "failed": failed,
        "num_workers": num_workers,
        "max_retries": max_retries,
        "output_files": {
            "json": str(json_file) if output_format in {"json", "both"} else None,
            "parquet": str(parquet_file) if output_format in {"parquet", "both"} else None,
        },
        "summary_stats": {
            "avg_yolo_pedestrians": (
                sum(r.get("yolo", {}).get("pedestrian_count", 0) for r in results) / len(results)
                if results
                else 0
            ),
            "avg_yolo_vehicles": (
                sum(r.get("yolo", {}).get("vehicle_count", 0) for r in results) / len(results)
                if results
                else 0
            ),
            "avg_d2_crowd_density": (
                sum(r.get("detectron2", {}).get("crowd_density", 0.0) for r in results) / len(results)
                if results
                else 0
            ),
        },
    }

    report_file = output_dir / f"extraction_report_{timestamp}.json"
    with report_file.open("w") as f:
        json.dump(summary, f, indent=2)

    LOGGER.info("Extraction report: %s", report_file)
    LOGGER.info("SUMMARY:")
    LOGGER.info("  Total images processed: %d", len(results))
    LOGGER.info("  Successful: %d", successful)
    LOGGER.info("  Failed: %d", failed)
    LOGGER.info("  Average pedestrians (YOLO): %.1f", summary["summary_stats"]["avg_yolo_pedestrians"])
    LOGGER.info("  Average vehicles (YOLO): %.1f", summary["summary_stats"]["avg_yolo_vehicles"])
    LOGGER.info("  Average crowd density (Detectron2): %.2f", summary["summary_stats"]["avg_d2_crowd_density"])

    return summary


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Batch process images with parallelization, retry logic, and checkpointing"
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        help="Directory containing images (default: auto-detect)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory for features (default: data/features)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "parquet", "both"],
        default="both",
        help="Output format (default: both)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        help="Number of parallel workers (default: CPU count)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum retry attempts per image (default: 3)",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=1.0,
        help="Delay between retries in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        help="Checkpoint file path for resuming (default: output_dir/checkpoint.json)",
    )
    parser.add_argument(
        "--checkpoint-interval",
        type=int,
        default=10,
        help="Save checkpoint every N images (default: 10)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of images to process (for testing)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )

    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Find images
    if args.input_dir:
        image_dirs = [args.input_dir]
    else:
        # Auto-detect: check both data/raw/images and backup location
        project_root = Path(__file__).parent.parent.parent
        image_dirs = [
            project_root / "data" / "raw" / "images",
            project_root / "docs" / "backup" / "data_bkup" / "raw" / "images",
        ]

    all_images = []
    for img_dir in image_dirs:
        images = find_all_images(img_dir)
        all_images.extend(images)
        if images:
            LOGGER.info("Found %d images in %s", len(images), img_dir)

    if not all_images:
        LOGGER.error("No images found!")
        sys.exit(1)

    # Remove duplicates
    all_images = list(set(all_images))
    all_images.sort()

    if args.limit:
        all_images = all_images[: args.limit]
        LOGGER.info("Limiting to %d images", args.limit)

    # Set up output directory
    if args.output_dir:
        output_dir = args.output_dir
    else:
        project_root = Path(__file__).parent.parent.parent
        output_dir = project_root / "data" / "features"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Set up checkpoint file
    checkpoint_file = args.checkpoint
    if checkpoint_file is None:
        checkpoint_file = output_dir / "checkpoint.json"

    # Process images
    process_images_batch(
        all_images,
        output_dir=output_dir,
        output_format=args.format,
        num_workers=args.workers,
        max_retries=args.max_retries,
        retry_delay=args.retry_delay,
        checkpoint_file=checkpoint_file,
        checkpoint_interval=args.checkpoint_interval,
        show_progress=True,
    )


if __name__ == "__main__":
    main()

