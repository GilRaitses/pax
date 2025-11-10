"""Visualize spatial coverage of image collection.

Maps which camera zones have images, shows coverage density, and identifies spatial gaps.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
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
        "--output",
        type=Path,
        default=Path("docs/figures/spatial_coverage.png"),
        help="Output path for spatial coverage plot (default: docs/figures/spatial_coverage.png)",
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


def load_spatial_data(
    zones_path: Path, cameras_path: Path, corridor_path: Path
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Load spatial data files."""
    zones = gpd.read_file(zones_path)
    cameras = gpd.read_file(cameras_path)
    corridor = gpd.read_file(corridor_path)
    return zones, cameras, corridor


def calculate_coverage_stats(
    manifest: dict[str, Any], zones: gpd.GeoDataFrame
) -> dict[str, Any]:
    """Calculate coverage statistics per zone."""
    cameras_data = manifest.get("cameras", {})
    zone_stats = defaultdict(lambda: {"image_count": 0, "has_images": False})

    # Map camera_id to zone
    camera_to_zone = {}
    if "camera_id" in zones.columns:
        for idx, row in zones.iterrows():
            camera_id = row.get("camera_id") or row.get("id")
            if camera_id:
                camera_to_zone[camera_id] = idx

    # Count images per camera/zone
    for camera_id, camera_data in cameras_data.items():
        image_count = camera_data.get("total_images", 0)
        zone_idx = camera_to_zone.get(camera_id)
        if zone_idx is not None:
            zone_stats[zone_idx]["image_count"] = image_count
            zone_stats[zone_idx]["has_images"] = image_count > 0

    return dict(zone_stats)


def plot_spatial_coverage(
    zones: gpd.GeoDataFrame,
    cameras: gpd.GeoDataFrame,
    corridor: gpd.GeoDataFrame,
    coverage_stats: dict[str, Any],
    output_path: Path,
) -> None:
    """Create spatial coverage visualization."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(20, 10))

    # Add coverage data to zones
    zones["image_count"] = 0
    zones["has_images"] = False
    for zone_idx, stats in coverage_stats.items():
        if zone_idx < len(zones):
            zones.iloc[zone_idx, zones.columns.get_loc("image_count")] = stats["image_count"]
            zones.iloc[zone_idx, zones.columns.get_loc("has_images")] = stats["has_images"]

    # Plot 1: Binary coverage (has images or not)
    ax1 = axes[0]
    corridor.plot(ax=ax1, color="lightgray", edgecolor="black", linewidth=1, alpha=0.3, label="Corridor")
    
    # Plot zones with no images
    zones_no_images = zones[~zones["has_images"]]
    if not zones_no_images.empty:
        zones_no_images.plot(ax=ax1, color="lightcoral", edgecolor="darkred", linewidth=0.5, alpha=0.6, label="No Images")
    
    # Plot zones with images
    zones_with_images = zones[zones["has_images"]]
    if not zones_with_images.empty:
        zones_with_images.plot(ax=ax1, color="lightgreen", edgecolor="darkgreen", linewidth=0.5, alpha=0.6, label="Has Images")
    
    # Plot cameras
    cameras.plot(ax=ax1, color="blue", markersize=30, marker="o", edgecolor="white", linewidth=1, label="Cameras", zorder=10)
    
    ax1.set_title("Spatial Coverage: Zones with Images", fontsize=14, fontweight="bold")
    ax1.set_xlabel("Longitude", fontsize=11)
    ax1.set_ylabel("Latitude", fontsize=11)
    ax1.legend(loc="upper right", fontsize=9)
    ax1.set_aspect("equal")
    ax1.grid(True, alpha=0.3)

    # Plot 2: Image count density
    ax2 = axes[1]
    corridor.plot(ax=ax2, color="lightgray", edgecolor="black", linewidth=1, alpha=0.3)
    
    # Plot zones colored by image count
    if not zones.empty:
        zones.plot(
            ax=ax2,
            column="image_count",
            cmap="YlOrRd",
            edgecolor="black",
            linewidth=0.5,
            legend=True,
            legend_kwds={"label": "Number of Images", "shrink": 0.8},
            vmin=0,
            vmax=max(zones["image_count"].max(), 1),
        )
    
    # Plot cameras with image count labels
    cameras_with_counts = cameras.copy()
    if "camera_id" in cameras.columns or "id" in cameras.columns:
        camera_id_col = "camera_id" if "camera_id" in cameras.columns else "id"
        # Merge with image counts from manifest
        # This is simplified - in practice you'd merge properly
        cameras_with_counts.plot(ax=ax2, color="blue", markersize=30, marker="o", edgecolor="white", linewidth=1, zorder=10)
    
    cameras.plot(ax=ax2, color="blue", markersize=30, marker="o", edgecolor="white", linewidth=1, zorder=10)
    
    ax2.set_title("Spatial Coverage: Image Count Density", fontsize=14, fontweight="bold")
    ax2.set_xlabel("Longitude", fontsize=11)
    ax2.set_ylabel("Latitude", fontsize=11)
    ax2.set_aspect("equal")
    ax2.grid(True, alpha=0.3)

    plt.suptitle("Spatial Coverage Analysis", fontsize=16, fontweight="bold", y=0.98)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    LOGGER.info("Spatial coverage plot saved to %s", output_path)


def identify_spatial_gaps(
    zones: gpd.GeoDataFrame, coverage_stats: dict[str, Any]
) -> None:
    """Identify and log spatial coverage gaps."""
    total_zones = len(zones)
    zones_with_images = sum(1 for stats in coverage_stats.values() if stats["has_images"])
    zones_without_images = total_zones - zones_with_images

    LOGGER.info("Spatial coverage summary:")
    LOGGER.info("  Total zones: %d", total_zones)
    LOGGER.info("  Zones with images: %d (%.1f%%)", zones_with_images, zones_with_images / total_zones * 100 if total_zones > 0 else 0)
    LOGGER.info("  Zones without images: %d (%.1f%%)", zones_without_images, zones_without_images / total_zones * 100 if total_zones > 0 else 0)

    # Find zones with most images
    if coverage_stats:
        max_images = max(stats["image_count"] for stats in coverage_stats.values())
        LOGGER.info("  Maximum images per zone: %d", max_images)

        # List zones with no images
        zones_no_images = [
            idx for idx, stats in coverage_stats.items() if not stats["has_images"]
        ]
        if zones_no_images:
            LOGGER.info("  Zones without images: %d zones", len(zones_no_images))


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=args.log_level.upper(), format="%(levelname)s: %(message)s"
    )

    if not args.manifest.exists():
        LOGGER.error("Manifest not found: %s", args.manifest)
        return 1

    if not args.zones.exists():
        LOGGER.error("Zones GeoJSON not found: %s", args.zones)
        return 1

    LOGGER.info("Loading manifest from %s", args.manifest)
    manifest = load_manifest(args.manifest)

    LOGGER.info("Loading spatial data...")
    zones, cameras, corridor = load_spatial_data(args.zones, args.cameras, args.corridor)

    LOGGER.info("Calculating coverage statistics...")
    coverage_stats = calculate_coverage_stats(manifest, zones)

    LOGGER.info("Identifying spatial gaps...")
    identify_spatial_gaps(zones, coverage_stats)

    LOGGER.info("Creating spatial coverage visualization...")
    plot_spatial_coverage(zones, cameras, corridor, coverage_stats, args.output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

