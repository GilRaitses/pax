"""Generate baseline heatmap visualization from stress scores.

Supports partial data visualization and is reusable for future updates.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import yaml

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--zones",
        type=Path,
        default=Path("data/geojson/voronoi_zones.geojson"),
        help="Path to Voronoi zones GeoJSON (default: data/geojson/voronoi_zones.geojson)",
    )
    parser.add_argument(
        "--cameras",
        type=Path,
        default=Path("data/geojson/corridor_cameras.geojson"),
        help="Path to cameras GeoJSON (default: data/geojson/corridor_cameras.geojson)",
    )
    parser.add_argument(
        "--corridor",
        type=Path,
        default=Path("data/geojson/corridor_polygon.geojson"),
        help="Path to corridor polygon GeoJSON (default: data/geojson/corridor_polygon.geojson)",
    )
    parser.add_argument(
        "--stress-scores",
        type=Path,
        help="Path to stress scores JSON file (camera_id -> stress_score). If not provided, will use zeros or manifest data.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/manifests/image_manifest.yaml"),
        help="Path to image manifest (used if stress-scores not provided, for partial data)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/figures/baseline_heatmap.png"),
        help="Output path for heatmap (default: docs/figures/baseline_heatmap.png)",
    )
    parser.add_argument(
        "--colormap",
        default="YlOrRd",
        help="Matplotlib colormap name (default: YlOrRd)",
    )
    parser.add_argument(
        "--vmin",
        type=float,
        help="Minimum value for color scale (auto if not provided)",
    )
    parser.add_argument(
        "--vmax",
        type=float,
        help="Maximum value for color scale (auto if not provided)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level",
    )
    return parser


def load_stress_scores(stress_path: Path | None, manifest_path: Path | None) -> dict[str, float]:
    """Load stress scores from file or generate from manifest."""
    stress_scores = {}

    if stress_path and stress_path.exists():
        LOGGER.info("Loading stress scores from %s", stress_path)
        with open(stress_path) as f:
            data = json.load(f)
            # Handle different JSON structures
            if isinstance(data, dict):
                stress_scores = data
            elif isinstance(data, list):
                # List of {camera_id, stress_score} objects
                stress_scores = {item["camera_id"]: item["stress_score"] for item in data}
            elif "camera_stress" in data:
                stress_scores = data["camera_stress"]
    elif manifest_path and manifest_path.exists():
        LOGGER.info("Generating placeholder stress scores from manifest (using image counts)")
        # Use image counts as placeholder stress scores
        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)
        cameras_data = manifest.get("cameras", {})
        for camera_id, camera_data in cameras_data.items():
            # Use image count as proxy for stress (more images = more data = higher confidence)
            image_count = camera_data.get("total_images", 0)
            stress_scores[camera_id] = float(image_count)  # Placeholder
        LOGGER.warning("Using image counts as placeholder stress scores. Provide --stress-scores for actual scores.")
    else:
        LOGGER.warning("No stress scores provided. Using zeros for all zones.")

    return stress_scores


def map_stress_to_zones(
    zones: gpd.GeoDataFrame, stress_scores: dict[str, float]
) -> gpd.GeoDataFrame:
    """Map stress scores to zones."""
    zones = zones.copy()
    zones["stress_score"] = np.nan
    zones["has_data"] = False

    # Try different column names for camera_id
    camera_id_col = None
    for col in ["camera_id", "id", "cameraId"]:
        if col in zones.columns:
            camera_id_col = col
            break

    if camera_id_col:
        for idx, row in zones.iterrows():
            camera_id = row[camera_id_col]
            if camera_id in stress_scores:
                zones.at[idx, "stress_score"] = stress_scores[camera_id]
                zones.at[idx, "has_data"] = True
    else:
        LOGGER.warning("Could not find camera_id column in zones. Stress scores may not be mapped correctly.")

    return zones


def plot_baseline_heatmap(
    zones: gpd.GeoDataFrame,
    cameras: gpd.GeoDataFrame,
    corridor: gpd.GeoDataFrame,
    output_path: Path,
    colormap: str = "YlOrRd",
    vmin: float | None = None,
    vmax: float | None = None,
) -> None:
    """Create baseline heatmap visualization."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(20, 10))

    # Determine color scale
    valid_scores = zones["stress_score"].dropna()
    if len(valid_scores) == 0:
        LOGGER.warning("No valid stress scores found. Using default range.")
        vmin_actual = vmin if vmin is not None else 0.0
        vmax_actual = vmax if vmax is not None else 1.0
    else:
        vmin_actual = vmin if vmin is not None else valid_scores.min()
        vmax_actual = vmax if vmax is not None else valid_scores.max()

    # Plot 1: Full heatmap (with NaN handling)
    ax1 = axes[0]
    corridor.plot(ax=ax1, color="lightgray", edgecolor="black", linewidth=1, alpha=0.3)

    # Plot zones with data
    zones_with_data = zones[zones["has_data"]]
    if not zones_with_data.empty:
        zones_with_data.plot(
            ax=ax1,
            column="stress_score",
            cmap=colormap,
            edgecolor="black",
            linewidth=0.5,
            legend=True,
            legend_kwds={"label": "Stress Score", "shrink": 0.8},
            vmin=vmin_actual,
            vmax=vmax_actual,
            missing_kwds={"color": "lightgray", "edgecolor": "red", "hatch": "///"},
        )

    # Plot zones without data
    zones_without_data = zones[~zones["has_data"]]
    if not zones_without_data.empty:
        zones_without_data.plot(
            ax=ax1,
            color="lightgray",
            edgecolor="red",
            linewidth=1,
            hatch="///",
            alpha=0.5,
            label="No Data",
        )

    cameras.plot(ax=ax1, color="blue", markersize=20, marker="o", edgecolor="white", linewidth=1, zorder=10)

    ax1.set_title("Baseline Stress Heatmap (Full Coverage)", fontsize=14, fontweight="bold")
    ax1.set_xlabel("Longitude", fontsize=11)
    ax1.set_ylabel("Latitude", fontsize=11)
    ax1.set_aspect("equal")
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc="upper right", fontsize=9)

    # Plot 2: Data availability overlay
    ax2 = axes[1]
    corridor.plot(ax=ax2, color="lightgray", edgecolor="black", linewidth=1, alpha=0.3)

    # Create binary coverage map
    zones["coverage"] = zones["has_data"].astype(int)
    zones.plot(
        ax=ax2,
        column="coverage",
        cmap="RdYlGn",
        edgecolor="black",
        linewidth=0.5,
        legend=True,
        legend_kwds={"labels": ["No Data", "Has Data"]},
        vmin=0,
        vmax=1,
        categorical=True,
    )

    cameras.plot(ax=ax2, color="blue", markersize=20, marker="o", edgecolor="white", linewidth=1, zorder=10)

    ax2.set_title("Data Availability Overlay", fontsize=14, fontweight="bold")
    ax2.set_xlabel("Longitude", fontsize=11)
    ax2.set_ylabel("Latitude", fontsize=11)
    ax2.set_aspect("equal")
    ax2.grid(True, alpha=0.3)

    # Add statistics text
    min_stress_str = f"{valid_scores.min():.2f}" if len(valid_scores) > 0 else "N/A"
    max_stress_str = f"{valid_scores.max():.2f}" if len(valid_scores) > 0 else "N/A"
    mean_stress_str = f"{valid_scores.mean():.2f}" if len(valid_scores) > 0 else "N/A"
    
    stats_text = f"""
Statistics:
- Zones with data: {zones['has_data'].sum()} / {len(zones)}
- Coverage: {zones['has_data'].sum() / len(zones) * 100:.1f}%
- Mean stress: {mean_stress_str}
- Min stress: {min_stress_str}
- Max stress: {max_stress_str}
"""
    fig.text(0.5, 0.02, stats_text, ha="center", fontsize=10, family="monospace")

    plt.suptitle("Baseline Stress Heatmap Visualization", fontsize=16, fontweight="bold", y=0.98)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    LOGGER.info("Baseline heatmap saved to %s", output_path)
    LOGGER.info("Zones with data: %d / %d (%.1f%%)", zones["has_data"].sum(), len(zones), zones["has_data"].sum() / len(zones) * 100)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=args.log_level.upper(), format="%(levelname)s: %(message)s"
    )

    if not args.zones.exists():
        LOGGER.error("Zones GeoJSON not found: %s", args.zones)
        return 1

    LOGGER.info("Loading spatial data...")
    zones = gpd.read_file(args.zones)
    cameras = gpd.read_file(args.cameras) if args.cameras.exists() else None
    corridor = gpd.read_file(args.corridor) if args.corridor.exists() else None

    LOGGER.info("Loading stress scores...")
    stress_scores = load_stress_scores(args.stress_scores, args.manifest)

    LOGGER.info("Mapping stress scores to zones...")
    zones = map_stress_to_zones(zones, stress_scores)

    LOGGER.info("Creating baseline heatmap visualization...")
    plot_baseline_heatmap(
        zones,
        cameras if cameras is not None else gpd.GeoDataFrame(),
        corridor if corridor is not None else gpd.GeoDataFrame(),
        args.output,
        args.colormap,
        args.vmin,
        args.vmax,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

