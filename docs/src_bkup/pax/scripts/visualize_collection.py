"""Visualize image collection statistics from manifest YAML."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import yaml


def load_manifest(manifest_path: Path) -> dict[str, Any]:
    """Load manifest YAML."""
    with open(manifest_path) as f:
        return yaml.safe_load(f)


def plot_images_over_time(manifest: dict[str, Any], output_path: Path | None = None) -> None:
    """Plot number of images collected over time."""
    stats = manifest.get("collection_stats", {})
    images_per_date = stats.get("images_per_date", {})
    
    if not images_per_date:
        print("No collection data found")
        return
    
    dates = [datetime.fromisoformat(d) for d in sorted(images_per_date.keys())]
    counts = [images_per_date[d] for d in sorted(images_per_date.keys())]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(dates, counts, marker="o", linewidth=2, markersize=6)
    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Images Collected", fontsize=12)
    ax.set_title("Image Collection Over Time", fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"Saved plot to {output_path}")
    else:
        plt.show()


def plot_camera_completion(manifest: dict[str, Any], output_path: Path | None = None) -> None:
    """Plot completion percentage per camera."""
    completion = manifest.get("completion_stats", {})
    
    if not completion:
        print("No completion stats found")
        return
    
    cameras = sorted(completion.keys())
    percentages = [completion[cam]["percentage_complete"] for cam in cameras]
    
    fig, ax = plt.subplots(figsize=(14, 8))
    bars = ax.barh(cameras, percentages, color="steelblue", alpha=0.7)
    ax.set_xlabel("Completion Percentage (%)", fontsize=12)
    ax.set_ylabel("Camera ID", fontsize=12)
    ax.set_title("Collection Completion by Camera", fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3, axis="x")
    
    # Add percentage labels on bars
    for i, (bar, pct) in enumerate(zip(bars, percentages)):
        width = bar.get_width()
        ax.text(width + 1, bar.get_y() + bar.get_height()/2, 
                f"{pct:.1f}%", ha="left", va="center", fontsize=9)
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"Saved plot to {output_path}")
    else:
        plt.show()


def plot_images_per_camera(manifest: dict[str, Any], output_path: Path | None = None) -> None:
    """Plot total images per camera."""
    cameras_data = manifest.get("cameras", {})
    
    if not cameras_data:
        print("No camera data found")
        return
    
    cameras = sorted(cameras_data.keys())
    counts = [cameras_data[cam]["total_images"] for cam in cameras]
    
    fig, ax = plt.subplots(figsize=(14, 8))
    bars = ax.barh(cameras, counts, color="coral", alpha=0.7)
    ax.set_xlabel("Total Images", fontsize=12)
    ax.set_ylabel("Camera ID", fontsize=12)
    ax.set_title("Total Images Collected per Camera", fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3, axis="x")
    
    # Add count labels
    for bar, count in zip(bars, counts):
        width = bar.get_width()
        ax.text(width + 0.5, bar.get_y() + bar.get_height()/2,
                str(count), ha="left", va="center", fontsize=9)
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"Saved plot to {output_path}")
    else:
        plt.show()


def plot_time_range_coverage(manifest: dict[str, Any], output_path: Path | None = None) -> None:
    """Plot time range coverage for each camera."""
    cameras_data = manifest.get("cameras", {})
    
    if not cameras_data:
        print("No camera data found")
        return
    
    fig, ax = plt.subplots(figsize=(14, max(8, len(cameras_data) * 0.3)))
    
    cameras = sorted(cameras_data.keys())
    y_positions = list(range(len(cameras)))
    
    for i, camera_id in enumerate(cameras):
        cam_data = cameras_data[camera_id]
        time_range = cam_data.get("time_range", {})
        earliest = datetime.fromisoformat(time_range.get("earliest", ""))
        latest = datetime.fromisoformat(time_range.get("latest", ""))
        
        # Draw horizontal bar representing time range
        ax.barh(i, (latest - earliest).total_seconds() / 3600 / 24,  # days
                left=mdates.date2num(earliest.date()),
                height=0.6, alpha=0.6, color="steelblue")
        
        # Add camera label
        ax.text(mdates.date2num(earliest.date()) - 0.5, i,
                camera_id[:20] + "..." if len(camera_id) > 20 else camera_id,
                ha="right", va="center", fontsize=8)
    
    ax.set_yticks(y_positions)
    ax.set_yticklabels([cam[:30] + "..." if len(cam) > 30 else cam for cam in cameras], fontsize=8)
    ax.set_xlabel("Date", fontsize=12)
    ax.set_title("Time Range Coverage per Camera", fontsize=14, fontweight="bold")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    ax.grid(True, alpha=0.3, axis="x")
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"Saved plot to {output_path}")
    else:
        plt.show()


def generate_summary_report(manifest: dict[str, Any]) -> None:
    """Print summary statistics."""
    metadata = manifest.get("metadata", {})
    cameras = manifest.get("cameras", {})
    completion = manifest.get("completion_stats", {})
    
    print("\n" + "="*60)
    print("COLLECTION SUMMARY REPORT")
    print("="*60)
    print(f"\nTotal Cameras: {metadata.get('total_cameras', 0)}")
    print(f"Total Images: {metadata.get('total_images', 0)}")
    
    period = metadata.get("collection_period", {})
    print(f"\nCollection Period:")
    print(f"  Start: {period.get('start_date', 'N/A')}")
    print(f"  End: {period.get('end_date', 'N/A')}")
    print(f"  Days: {period.get('total_days', 0)}")
    
    if completion:
        avg_completion = sum(c["percentage_complete"] for c in completion.values()) / len(completion)
        print(f"\nAverage Completion: {avg_completion:.2f}%")
        
        print(f"\nTop 5 Cameras by Completion:")
        sorted_cams = sorted(completion.items(), key=lambda x: x[1]["percentage_complete"], reverse=True)
        for camera_id, stats in sorted_cams[:5]:
            print(f"  {camera_id[:40]}: {stats['percentage_complete']:.1f}% "
                  f"({stats['actual_images']}/{stats['expected_images']} images)")
    
    print("\n" + "="*60 + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Visualize image collection from manifest")
    parser.add_argument("manifest", type=Path, help="Path to manifest YAML")
    parser.add_argument("--output-dir", type=Path, help="Directory to save plots (default: show plots)")
    parser.add_argument("--summary", action="store_true", help="Print summary report")
    
    args = parser.parse_args()
    
    if not args.manifest.exists():
        print(f"Error: Manifest not found: {args.manifest}", file=sys.stderr)
        return 1
    
    manifest = load_manifest(args.manifest)
    
    if args.summary:
        generate_summary_report(manifest)
    
    output_dir = args.output_dir
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
    
    print("Generating visualizations...")
    
    plot_images_over_time(manifest, output_dir / "images_over_time.png" if output_dir else None)
    plot_camera_completion(manifest, output_dir / "completion_by_camera.png" if output_dir else None)
    plot_images_per_camera(manifest, output_dir / "images_per_camera.png" if output_dir else None)
    plot_time_range_coverage(manifest, output_dir / "time_coverage.png" if output_dir else None)
    
    print("Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())



