"""Assess image quality from manifest and image files.

Checks image resolution, clarity, and identifies corrupted/missing images.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from PIL import Image, ImageStat

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/manifests/image_manifest.yaml"),
        help="Path to image manifest YAML",
    )
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=Path("data/raw/images"),
        help="Base directory containing images (default: data/raw/images)",
    )
    parser.add_argument(
        "--output-report",
        type=Path,
        default=Path("docs/reports/image_quality_report.md"),
        help="Path to save quality report (default: docs/reports/image_quality_report.md)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level",
    )
    return parser


def load_manifest(manifest_path: Path) -> dict[str, Any]:
    """Load manifest YAML."""
    with open(manifest_path) as f:
        return yaml.safe_load(f)


def assess_image_quality(image_path: Path) -> dict[str, Any]:
    """Assess quality of a single image."""
    result = {
        "exists": False,
        "corrupted": False,
        "width": None,
        "height": None,
        "resolution": None,
        "file_size": None,
        "brightness": None,
        "contrast": None,
        "error": None,
    }

    if not image_path.exists():
        result["error"] = "File not found"
        return result

    result["exists"] = True
    result["file_size"] = image_path.stat().st_size

    try:
        with Image.open(image_path) as img:
            result["width"] = img.width
            result["height"] = img.height
            result["resolution"] = img.width * img.height

            # Convert to RGB if needed for statistics
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Calculate image statistics
            stat = ImageStat.Stat(img)
            # Brightness: mean of all channels
            result["brightness"] = sum(stat.mean) / len(stat.mean)
            # Contrast: standard deviation of all channels
            result["contrast"] = sum(stat.stddev) / len(stat.stddev) if stat.stddev else 0

    except Exception as e:
        result["corrupted"] = True
        result["error"] = str(e)

    return result


def assess_all_images(
    manifest: dict[str, Any], images_dir: Path
) -> dict[str, Any]:
    """Assess quality of all images in manifest."""
    cameras_data = manifest.get("cameras", {})
    results = {
        "total_images": 0,
        "assessed_images": 0,
        "missing_images": 0,
        "corrupted_images": 0,
        "camera_results": {},
        "quality_stats": {
            "resolutions": [],
            "file_sizes": [],
            "brightness": [],
            "contrast": [],
        },
    }

    for camera_id, camera_data in cameras_data.items():
        camera_results = {
            "camera_id": camera_id,
            "total_images": camera_data.get("total_images", 0),
            "assessed": 0,
            "missing": 0,
            "corrupted": 0,
            "images": [],
        }

        for image_info in camera_data.get("images", []):
            results["total_images"] += 1
            local_path = image_info.get("local_path")
            if not local_path:
                camera_results["missing"] += 1
                results["missing_images"] += 1
                continue

            # Try to resolve image path
            image_path = None
            if Path(local_path).is_absolute():
                image_path = Path(local_path)
            else:
                # Try relative to images_dir
                image_path = images_dir / local_path
                if not image_path.exists():
                    # Try with date directory structure
                    date = image_info.get("date")
                    if date:
                        image_path = images_dir / date / Path(local_path).name
                    if not image_path.exists():
                        # Try camera_id subdirectory structure
                        image_path = images_dir / camera_id / Path(local_path).name

            quality = assess_image_quality(image_path)
            camera_results["assessed"] += 1
            results["assessed_images"] += 1

            if not quality["exists"]:
                camera_results["missing"] += 1
                results["missing_images"] += 1
            elif quality["corrupted"]:
                camera_results["corrupted"] += 1
                results["corrupted_images"] += 1
            else:
                # Collect statistics
                if quality["resolution"]:
                    results["quality_stats"]["resolutions"].append(quality["resolution"])
                if quality["file_size"]:
                    results["quality_stats"]["file_sizes"].append(quality["file_size"])
                if quality["brightness"]:
                    results["quality_stats"]["brightness"].append(quality["brightness"])
                if quality["contrast"]:
                    results["quality_stats"]["contrast"].append(quality["contrast"])

            image_result = {
                "timestamp": image_info.get("timestamp"),
                "path": str(image_path) if image_path else local_path,
                "quality": quality,
            }
            camera_results["images"].append(image_result)

        results["camera_results"][camera_id] = camera_results

    return results


def generate_report(assessment_results: dict[str, Any], output_path: Path) -> None:
    """Generate markdown quality report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    stats = assessment_results["quality_stats"]
    total = assessment_results["total_images"]
    assessed = assessment_results["assessed_images"]
    missing = assessment_results["missing_images"]
    corrupted = assessment_results["corrupted_images"]

    with open(output_path, "w") as f:
        f.write("# Image Quality Assessment Report\n\n")
        f.write(f"**Generated:** {Path(__file__).stat().st_mtime}\n\n")

        f.write("## Summary\n\n")
        f.write(f"- **Total Images:** {total}\n")
        f.write(f"- **Assessed:** {assessed}\n")
        f.write(f"- **Missing:** {missing} ({missing/total*100:.1f}%)\n")
        f.write(f"- **Corrupted:** {corrupted} ({corrupted/total*100:.1f}%)\n")
        f.write(f"- **Valid:** {assessed - missing - corrupted}\n\n")

        if stats["resolutions"]:
            resolutions = np.array(stats["resolutions"])
            f.write("## Resolution Statistics\n\n")
            f.write(f"- **Mean:** {resolutions.mean():.0f} pixels\n")
            f.write(f"- **Median:** {np.median(resolutions):.0f} pixels\n")
            f.write(f"- **Min:** {resolutions.min():.0f} pixels\n")
            f.write(f"- **Max:** {resolutions.max():.0f} pixels\n")
            f.write(f"- **Std Dev:** {resolutions.std():.0f} pixels\n\n")

        if stats["file_sizes"]:
            file_sizes = np.array(stats["file_sizes"])
            f.write("## File Size Statistics\n\n")
            f.write(f"- **Mean:** {file_sizes.mean()/1024:.1f} KB\n")
            f.write(f"- **Median:** {np.median(file_sizes)/1024:.1f} KB\n")
            f.write(f"- **Min:** {file_sizes.min()/1024:.1f} KB\n")
            f.write(f"- **Max:** {file_sizes.max()/1024:.1f} KB\n\n")

        if stats["brightness"]:
            brightness = np.array(stats["brightness"])
            f.write("## Brightness Statistics\n\n")
            f.write(f"- **Mean:** {brightness.mean():.1f}\n")
            f.write(f"- **Median:** {np.median(brightness):.1f}\n")
            f.write(f"- **Min:** {brightness.min():.1f}\n")
            f.write(f"- **Max:** {brightness.max():.1f}\n\n")

        if stats["contrast"]:
            contrast = np.array(stats["contrast"])
            f.write("## Contrast Statistics\n\n")
            f.write(f"- **Mean:** {contrast.mean():.1f}\n")
            f.write(f"- **Median:** {np.median(contrast):.1f}\n")
            f.write(f"- **Min:** {contrast.min():.1f}\n")
            f.write(f"- **Max:** {contrast.max():.1f}\n\n")

        # Camera-level summary
        f.write("## Camera-Level Summary\n\n")
        f.write("| Camera ID | Total | Assessed | Missing | Corrupted | Status |\n")
        f.write("|-----------|-------|----------|--------|-----------|--------|\n")

        for camera_id, camera_result in sorted(
            assessment_results["camera_results"].items()
        ):
            status = "OK"
            if camera_result["corrupted"] > 0:
                status = "CORRUPTED"
            elif camera_result["missing"] == camera_result["total_images"]:
                status = "ALL_MISSING"
            elif camera_result["missing"] > 0:
                status = "PARTIAL"

            f.write(
                f"| {camera_id[:40]}... | {camera_result['total_images']} | "
                f"{camera_result['assessed']} | {camera_result['missing']} | "
                f"{camera_result['corrupted']} | {status} |\n"
            )

        # List corrupted images
        corrupted_list = []
        for camera_id, camera_result in assessment_results["camera_results"].items():
            for img in camera_result["images"]:
                if img["quality"].get("corrupted"):
                    corrupted_list.append(
                        {
                            "camera_id": camera_id,
                            "timestamp": img.get("timestamp"),
                            "path": img.get("path"),
                            "error": img["quality"].get("error"),
                        }
                    )

        if corrupted_list:
            f.write("\n## Corrupted Images\n\n")
            f.write("| Camera ID | Timestamp | Path | Error |\n")
            f.write("|-----------|-----------|------|-------|\n")
            for item in corrupted_list[:50]:  # Limit to first 50
                f.write(
                    f"| {item['camera_id'][:30]}... | {item.get('timestamp', 'N/A')} | "
                    f"{item.get('path', 'N/A')[:50]}... | {item.get('error', 'N/A')[:50]} |\n"
                )
            if len(corrupted_list) > 50:
                f.write(f"\n*... and {len(corrupted_list) - 50} more corrupted images*\n")

    LOGGER.info("Quality report written to %s", output_path)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=args.log_level.upper(), format="%(levelname)s: %(message)s"
    )

    if not args.manifest.exists():
        LOGGER.error("Manifest not found: %s", args.manifest)
        return 1

    LOGGER.info("Loading manifest from %s", args.manifest)
    manifest = load_manifest(args.manifest)

    LOGGER.info("Assessing image quality...")
    results = assess_all_images(manifest, args.images_dir)

    LOGGER.info("Generating quality report...")
    generate_report(results, args.output_report)

    LOGGER.info("Assessment complete:")
    LOGGER.info("  Total images: %d", results["total_images"])
    LOGGER.info("  Assessed: %d", results["assessed_images"])
    LOGGER.info("  Missing: %d", results["missing_images"])
    LOGGER.info("  Corrupted: %d", results["corrupted_images"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

