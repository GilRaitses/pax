"""Visualize temporal coverage of image collection.

Plots images by time of day, shows coverage gaps, and identifies peak collection times.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import yaml

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
        "--output",
        type=Path,
        default=Path("docs/figures/temporal_coverage.png"),
        help="Output path for temporal coverage plot (default: docs/figures/temporal_coverage.png)",
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


def extract_temporal_data(manifest: dict[str, Any]) -> dict[str, Any]:
    """Extract temporal data from manifest."""
    cameras_data = manifest.get("cameras", {})
    timestamps = []
    hourly_counts = defaultdict(int)
    daily_counts = defaultdict(int)
    day_of_week_counts = defaultdict(int)

    for camera_id, camera_data in cameras_data.items():
        for image_info in camera_data.get("images", []):
            timestamp_str = image_info.get("timestamp")
            if not timestamp_str:
                continue

            try:
                dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                timestamps.append(dt)
                hourly_counts[dt.hour] += 1
                daily_counts[dt.date()] += 1
                day_of_week_counts[dt.weekday()] += 1
            except Exception as e:
                LOGGER.warning("Failed to parse timestamp %s: %s", timestamp_str, e)

    return {
        "timestamps": timestamps,
        "hourly_counts": dict(hourly_counts),
        "daily_counts": dict(daily_counts),
        "day_of_week_counts": dict(day_of_week_counts),
    }


def plot_temporal_coverage(temporal_data: dict[str, Any], output_path: Path) -> None:
    """Create temporal coverage visualization."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    timestamps = temporal_data["timestamps"]
    hourly_counts = temporal_data["hourly_counts"]
    daily_counts = temporal_data["daily_counts"]

    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)

    # 1. Hourly distribution (bar chart)
    ax1 = fig.add_subplot(gs[0, 0])
    hours = sorted(hourly_counts.keys())
    counts = [hourly_counts[h] for h in hours]
    bars = ax1.bar(hours, counts, color="steelblue", alpha=0.7, edgecolor="black", linewidth=0.5)
    ax1.set_xlabel("Hour of Day", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Number of Images", fontsize=11, fontweight="bold")
    ax1.set_title("Images by Hour of Day", fontsize=12, fontweight="bold")
    ax1.set_xticks(range(0, 24, 2))
    ax1.grid(True, alpha=0.3, axis="y")
    ax1.set_xlim(-0.5, 23.5)

    # Add value labels on bars
    for bar, count in zip(bars, counts):
        if count > 0:
            height = bar.get_height()
            ax1.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{count}",
                ha="center",
                va="bottom",
                fontsize=8,
            )

    # Identify peak hours
    if counts:
        peak_hour = hours[np.argmax(counts)]
        ax1.axvline(peak_hour, color="red", linestyle="--", linewidth=2, alpha=0.5, label=f"Peak: {peak_hour}:00")
        ax1.legend()

    # 2. Timeline scatter plot
    ax2 = fig.add_subplot(gs[0, 1])
    if timestamps:
        df = pd.DataFrame({"timestamp": timestamps})
        df["hour"] = df["timestamp"].dt.hour
        df["minute"] = df["timestamp"].dt.minute
        df["time_of_day"] = df["hour"] + df["minute"] / 60.0

        ax2.scatter(
            df["timestamp"],
            df["time_of_day"],
            alpha=0.4,
            s=20,
            color="coral",
            edgecolors="black",
            linewidth=0.3,
        )
        ax2.set_xlabel("Date", fontsize=11, fontweight="bold")
        ax2.set_ylabel("Hour of Day", fontsize=11, fontweight="bold")
        ax2.set_title("Collection Timeline", fontsize=12, fontweight="bold")
        ax2.set_ylim(-0.5, 23.5)
        ax2.set_yticks(range(0, 24, 4))
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        ax2.xaxis.set_major_locator(mdates.DayLocator(interval=1))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha="right")

    # 3. Daily collection counts
    ax3 = fig.add_subplot(gs[1, :])
    if daily_counts:
        dates = sorted(daily_counts.keys())
        counts = [daily_counts[d] for d in dates]
        bars = ax3.bar(range(len(dates)), counts, color="mediumseagreen", alpha=0.7, edgecolor="black", linewidth=0.5)
        ax3.set_xlabel("Date", fontsize=11, fontweight="bold")
        ax3.set_ylabel("Number of Images", fontsize=11, fontweight="bold")
        ax3.set_title("Images Collected per Day", fontsize=12, fontweight="bold")
        ax3.set_xticks(range(len(dates)))
        ax3.set_xticklabels([d.strftime("%Y-%m-%d") for d in dates], rotation=45, ha="right")
        ax3.grid(True, alpha=0.3, axis="y")

        # Add value labels
        for bar, count in zip(bars, counts):
            height = bar.get_height()
            ax3.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{count}",
                ha="center",
                va="bottom",
                fontsize=9,
            )

    # 4. Coverage gaps analysis
    ax4 = fig.add_subplot(gs[2, :])
    if timestamps:
        # Create hourly bins for all hours in date range
        if timestamps:
            min_date = min(timestamps).date()
            max_date = max(timestamps).date()
            all_hours = []
            current_date = min_date
            while current_date <= max_date:
                for hour in range(24):
                    all_hours.append((current_date, hour))
                current_date = pd.Timestamp(current_date) + pd.Timedelta(days=1)
                current_date = current_date.date()

            # Count images per hour
            hour_coverage = defaultdict(int)
            for ts in timestamps:
                hour_coverage[(ts.date(), ts.hour)] += 1

            # Create coverage matrix
            dates = sorted(set(d for d, _ in all_hours))
            hours = list(range(24))
            coverage_matrix = np.zeros((len(dates), len(hours)))

            for i, date in enumerate(dates):
                for j, hour in enumerate(hours):
                    coverage_matrix[i, j] = hour_coverage.get((date, hour), 0)

            im = ax4.imshow(
                coverage_matrix,
                aspect="auto",
                cmap="YlOrRd",
                interpolation="nearest",
                origin="lower",
            )
            ax4.set_xlabel("Hour of Day", fontsize=11, fontweight="bold")
            ax4.set_ylabel("Date", fontsize=11, fontweight="bold")
            ax4.set_title("Temporal Coverage Heatmap (Images per Hour)", fontsize=12, fontweight="bold")
            ax4.set_xticks(range(0, 24, 2))
            ax4.set_xticklabels(range(0, 24, 2))
            ax4.set_yticks(range(len(dates)))
            ax4.set_yticklabels([d.strftime("%Y-%m-%d") for d in dates])
            plt.colorbar(im, ax=ax4, label="Number of Images")

    plt.suptitle("Temporal Coverage Analysis", fontsize=14, fontweight="bold", y=0.995)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    LOGGER.info("Temporal coverage plot saved to %s", output_path)


def identify_coverage_gaps(temporal_data: dict[str, Any]) -> None:
    """Identify and log coverage gaps."""
    hourly_counts = temporal_data["hourly_counts"]
    all_hours = set(range(24))
    covered_hours = set(hourly_counts.keys())
    gap_hours = sorted(all_hours - covered_hours)

    if gap_hours:
        LOGGER.info("Coverage gaps identified:")
        LOGGER.info("  Hours with no images: %s", gap_hours)
    else:
        LOGGER.info("All hours have at least some coverage")

    # Identify peak collection times
    if hourly_counts:
        peak_hour = max(hourly_counts.items(), key=lambda x: x[1])
        LOGGER.info("Peak collection hour: %d:00 (%d images)", peak_hour[0], peak_hour[1])


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

    LOGGER.info("Extracting temporal data...")
    temporal_data = extract_temporal_data(manifest)

    LOGGER.info("Identifying coverage gaps...")
    identify_coverage_gaps(temporal_data)

    LOGGER.info("Creating temporal coverage visualization...")
    plot_temporal_coverage(temporal_data, args.output)

    LOGGER.info("Total images analyzed: %d", len(temporal_data["timestamps"]))
    LOGGER.info("Date range: %s to %s",
                min(temporal_data["timestamps"]).date() if temporal_data["timestamps"] else "N/A",
                max(temporal_data["timestamps"]).date() if temporal_data["timestamps"] else "N/A")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

