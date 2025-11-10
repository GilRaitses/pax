#!/usr/bin/env python3
"""Feature extraction monitoring and reporting.

This script tracks extraction progress, monitors errors and failures,
and generates extraction reports.
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from pax.storage.feature_query import FeatureQuery

LOGGER = logging.getLogger(__name__)


def load_extraction_reports(reports_dir: Path) -> list[dict[str, Any]]:
    """Load all extraction reports from the reports directory."""
    reports = []
    if not reports_dir.exists():
        return reports

    for report_file in reports_dir.glob("extraction_report_*.json"):
        try:
            with report_file.open("r") as f:
                report = json.load(f)
                report["report_file"] = str(report_file)
                reports.append(report)
        except Exception as e:
            LOGGER.warning("Failed to load report %s: %s", report_file, e)

    return sorted(reports, key=lambda x: x.get("timestamp", ""), reverse=True)


def load_checkpoint(checkpoint_file: Path) -> dict[str, Any] | None:
    """Load checkpoint file if it exists."""
    if not checkpoint_file.exists():
        return None

    try:
        with checkpoint_file.open("r") as f:
            return json.load(f)
    except Exception as e:
        LOGGER.warning("Failed to load checkpoint: %s", e)
        return None


def generate_progress_report(
    features_dir: Path,
    reports_dir: Path | None = None,
    checkpoint_file: Path | None = None,
) -> dict[str, Any]:
    """Generate progress report from features and reports."""
    if reports_dir is None:
        reports_dir = features_dir

    # Load extraction reports
    reports = load_extraction_reports(reports_dir)

    # Load checkpoint if available
    checkpoint = None
    if checkpoint_file:
        checkpoint = load_checkpoint(checkpoint_file)
    elif features_dir.exists():
        checkpoint_file = features_dir / "checkpoint.json"
        checkpoint = load_checkpoint(checkpoint_file)

    # Query feature storage
    query = FeatureQuery(features_dir)
    time_range = query.get_time_range()
    camera_list = query.get_camera_list()

    # Aggregate statistics
    stats = query.aggregate_statistics()

    # Calculate progress metrics
    total_images = stats.get("count", 0)
    successful_images = total_images  # Assume all stored features are successful

    # Get error statistics from reports
    total_processed = 0
    total_successful = 0
    total_failed = 0
    error_summary = {}

    for report in reports:
        total_processed += report.get("total_images", 0)
        total_successful += report.get("successful", 0)
        total_failed += report.get("failed", 0)

    if checkpoint:
        checkpoint_stats = checkpoint.get("stats", {})
        total_processed = checkpoint_stats.get("total_processed", total_processed)
        total_successful = checkpoint_stats.get("successful", total_successful)
        total_failed = checkpoint_stats.get("failed", total_failed)

    progress_report = {
        "generated_at": datetime.now().isoformat(),
        "features_stored": {
            "total_images": total_images,
            "cameras": len(camera_list),
            "time_range": {
                "start": time_range.get("start_time").isoformat() if time_range.get("start_time") else None,
                "end": time_range.get("end_time").isoformat() if time_range.get("end_time") else None,
            },
        },
        "extraction_progress": {
            "total_processed": total_processed,
            "successful": total_successful,
            "failed": total_failed,
            "success_rate": (total_successful / total_processed * 100) if total_processed > 0 else 0,
        },
        "statistics": stats,
        "reports": {
            "count": len(reports),
            "latest": reports[0] if reports else None,
        },
        "checkpoint": checkpoint is not None,
    }

    return progress_report


def generate_error_report(features_dir: Path, reports_dir: Path | None = None) -> dict[str, Any]:
    """Generate error report from extraction reports."""
    if reports_dir is None:
        reports_dir = features_dir

    reports = load_extraction_reports(reports_dir)

    error_summary = {
        "total_failed": 0,
        "total_errors": 0,
        "error_types": {},
        "failed_images": [],
    }

    # Load features to check for errors
    parquet_file = features_dir / "parquet" / "features.parquet"
    if parquet_file.exists():
        df = pd.read_parquet(parquet_file)
        if "has_errors" in df.columns:
            failed_df = df[df["has_errors"] == True]
            error_summary["total_failed"] = len(failed_df)

            if "error_count" in df.columns:
                error_summary["total_errors"] = int(df["error_count"].sum())

            # Collect failed image paths
            if "image_path" in failed_df.columns:
                error_summary["failed_images"] = failed_df["image_path"].tolist()

    # Aggregate from reports
    for report in reports:
        failed = report.get("failed", 0)
        error_summary["total_failed"] += failed

    return error_summary


def print_progress_dashboard(report: dict[str, Any]) -> None:
    """Print a formatted progress dashboard."""
    print("=" * 80)
    print("FEATURE EXTRACTION MONITORING DASHBOARD")
    print("=" * 80)
    print(f"Generated at: {report['generated_at']}")
    print()

    # Features stored
    features = report.get("features_stored", {})
    print("FEATURES STORED:")
    print(f"  Total images: {features.get('total_images', 0)}")
    print(f"  Cameras: {features.get('cameras', 0)}")
    time_range = features.get("time_range", {})
    if time_range.get("start"):
        print(f"  Start time: {time_range['start']}")
    if time_range.get("end"):
        print(f"  End time: {time_range['end']}")
    print()

    # Extraction progress
    progress = report.get("extraction_progress", {})
    print("EXTRACTION PROGRESS:")
    print(f"  Total processed: {progress.get('total_processed', 0)}")
    print(f"  Successful: {progress.get('successful', 0)}")
    print(f"  Failed: {progress.get('failed', 0)}")
    print(f"  Success rate: {progress.get('success_rate', 0):.1f}%")
    print()

    # Statistics summary
    stats = report.get("statistics", {})
    if stats.get("count", 0) > 0:
        print("STATISTICS SUMMARY:")
        print(f"  Average pedestrians: {stats.get('spatial_pedestrian_count_mean', 0):.1f}")
        print(f"  Average vehicles: {stats.get('spatial_vehicle_count_mean', 0):.1f}")
        print(f"  Average crowd density: {stats.get('spatial_crowd_density_mean', 0):.2f}")
        print()

    # Reports
    reports_info = report.get("reports", {})
    print("REPORTS:")
    print(f"  Total reports: {reports_info.get('count', 0)}")
    latest = reports_info.get("latest")
    if latest:
        print(f"  Latest report: {latest.get('timestamp', 'N/A')}")
    print()

    # Checkpoint status
    print(f"Checkpoint available: {'Yes' if report.get('checkpoint') else 'No'}")
    print("=" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Monitor feature extraction progress")
    parser.add_argument(
        "--features-dir",
        type=Path,
        help="Directory containing features (default: data/features)",
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        help="Directory containing extraction reports (default: same as features-dir)",
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        help="Checkpoint file path (default: features-dir/checkpoint.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file for progress report (default: print to stdout)",
    )
    parser.add_argument(
        "--error-report",
        action="store_true",
        help="Generate error report instead of progress report",
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

    # Set up directories
    if args.features_dir:
        features_dir = args.features_dir
    else:
        project_root = Path(__file__).parent.parent.parent
        features_dir = project_root / "data" / "features"

    reports_dir = args.reports_dir or features_dir
    checkpoint_file = args.checkpoint or (features_dir / "checkpoint.json")

    # Generate report
    if args.error_report:
        report = generate_error_report(features_dir, reports_dir)
        report_type = "error"
    else:
        report = generate_progress_report(features_dir, reports_dir, checkpoint_file)
        report_type = "progress"

    # Output report
    if args.output:
        with args.output.open("w") as f:
            json.dump(report, f, indent=2, default=str)
        LOGGER.info("Saved %s report to: %s", report_type, args.output)
    else:
        if report_type == "progress":
            print_progress_dashboard(report)
        else:
            print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()

