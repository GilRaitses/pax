"""Generate Voronoi tessellation map matching the proposal style.

Shows all Voronoi zones with cameras, intersections, and street network.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import yaml
from scipy.spatial import Voronoi

from ..config import PaxSettings

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--zones",
        type=Path,
        default=Path("data/voronoi_zones/voronoi_zones.geojson"),
        help="Voronoi zones GeoJSON file",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("cameras.yaml"),
        help="Camera manifest YAML file",
    )
    parser.add_argument(
        "--dcm-shapefile",
        type=Path,
        help="DCM StreetCenterLine shapefile path",
    )
    parser.add_argument(
        "--intersections",
        type=Path,
        help="Intersections JSON file (optional)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/voronoi_zones/voronoi_tessellation_map.png"),
        help="Output image path",
    )
    parser.add_argument(
        "--bounds",
        nargs=4,
        type=float,
        metavar=("LAT_MIN", "LAT_MAX", "LON_MIN", "LON_MAX"),
        default=(40.744, 40.773, -74.003, -73.967),
        help="Map bounds (default: corridor bounds)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="Output DPI (default: 300)",
    )
    parser.add_argument(
        "--figsize",
        nargs=2,
        type=float,
        default=(22, 18),
        help="Figure size in inches (default: 22 18)",
    )
    return parser


def load_zones(zones_path: Path) -> gpd.GeoDataFrame:
    """Load Voronoi zones."""
    zones = gpd.read_file(zones_path)
    LOGGER.info("Loaded %d Voronoi zones", len(zones))
    return zones


def load_cameras(manifest_path: Path) -> list[dict]:
    """Load camera locations."""
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)
    cameras = manifest.get("cameras", [])
    LOGGER.info("Loaded %d cameras", len(cameras))
    return cameras


def load_streets(dcm_path: Path, bounds: tuple[float, float, float, float]) -> gpd.GeoDataFrame:
    """Load and filter street centerlines."""
    LOGGER.info("Loading DCM street centerlines from %s", dcm_path)
    dcm = gpd.read_file(dcm_path)
    
    # Convert to EPSG:4326 if needed
    if dcm.crs != "EPSG:4326":
        LOGGER.info("Converting DCM from %s to EPSG:4326", dcm.crs)
        dcm = dcm.to_crs(epsg=4326)
    
    # Filter Manhattan
    if "Borough" in dcm.columns:
        manhattan = dcm[dcm["Borough"] == "Manhattan"].copy()
    else:
        manhattan = dcm.copy()
    
    # Filter to bounds
    lat_min, lat_max, lon_min, lon_max = bounds
    corridor_streets = manhattan.cx[lon_min:lon_max, lat_min:lat_max]
    
    LOGGER.info("Found %d street segments in corridor", len(corridor_streets))
    return corridor_streets


def load_intersections(intersections_path: Path | None) -> np.ndarray | None:
    """Load intersection coordinates if provided."""
    if intersections_path is None or not intersections_path.exists():
        return None
    
    with open(intersections_path) as f:
        data = json.load(f)
    
    if isinstance(data, dict) and "coordinates" in data:
        coords = np.array(data["coordinates"])
    elif isinstance(data, list):
        coords = np.array(data)
    else:
        return None
    
    LOGGER.info("Loaded %d intersections", len(coords))
    return coords


def create_voronoi_visualization(
    zones: gpd.GeoDataFrame,
    cameras: list[dict],
    streets: gpd.GeoDataFrame | None = None,
    intersections: np.ndarray | None = None,
    bounds: tuple[float, float, float, float] = (40.744, 40.773, -74.003, -73.967),
    output_path: Path | None = None,
    figsize: tuple[float, float] = (22, 18),
    dpi: int = 300,
) -> None:
    """Create Voronoi tessellation map matching proposal style."""
    
    lat_min, lat_max, lon_min, lon_max = bounds
    
    # Create figure
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    
    # Plot street network (dark gray, thicker) - if provided
    if streets is not None and len(streets) > 0:
        streets.plot(ax=ax, color="#2c3e50", linewidth=1.8, alpha=0.7, zorder=2)
    
    # Plot Voronoi tessellation (soft yellow/gold, semi-opaque)
    # Create multiple layers for blurry effect like proposal
    for zone in zones.itertuples():
        geom = zone.geometry
        if geom.geom_type == "Polygon":
            # Create soft blurry effect with multiple transparent layers
            for width, alpha in [(12, 0.05), (10, 0.08), (8, 0.1), (6, 0.12), (4, 0.15), (2, 0.18)]:
                if geom.geom_type == "Polygon":
                    x, y = geom.exterior.xy
                    ax.plot(x, y, color="#ffd700", linewidth=width, alpha=alpha, 
                           zorder=3, linestyle="-", solid_capstyle="round")
        elif geom.geom_type == "MultiPolygon":
            for poly in geom.geoms:
                x, y = poly.exterior.xy
                for width, alpha in [(12, 0.05), (10, 0.08), (8, 0.1), (6, 0.12), (4, 0.15), (2, 0.18)]:
                    ax.plot(x, y, color="#ffd700", linewidth=width, alpha=alpha,
                           zorder=3, linestyle="-", solid_capstyle="round")
    
    # Plot intersection nodes (WHITE circles with RED borders) - if provided
    if intersections is not None and len(intersections) > 0:
        ax.scatter(intersections[:, 0], intersections[:, 1],
                  s=60, c="white", edgecolor="#c0392b", linewidth=2.5,
                  zorder=5, alpha=0.95, label=f"{len(intersections)} intersection nodes")
    
    # Plot cameras (GREEN triangles, larger)
    camera_coords = []
    camera_names = []
    for cam in cameras:
        lat = cam.get("latitude")
        lon = cam.get("longitude")
        if lat is not None and lon is not None:
            camera_coords.append([lon, lat])
            camera_names.append(cam.get("name", ""))
    
    if len(camera_coords) > 0:
        camera_coords = np.array(camera_coords)
        ax.scatter(camera_coords[:, 0], camera_coords[:, 1],
                  s=220, c="#27ae60", edgecolor="#196f3d", linewidth=3,
                  zorder=6, alpha=0.95, label=f"{len(camera_coords)} cameras", marker="^")
    
    # Mark start and goal
    gc_lon, gc_lat = -73.9772, 40.7527
    ch_lon, ch_lat = -73.9799, 40.7651
    
    # START (Grand Central)
    ax.scatter(gc_lon, gc_lat, s=1400, c="#3498db", edgecolor="#1a5276",
              linewidth=5, marker="*", zorder=9)
    ax.annotate("START (s₀)\nGrand Central\n42nd & Park",
               xy=(gc_lon, gc_lat), xytext=(gc_lon + 0.0015, gc_lat - 0.002),
               ha="left", va="top",
               fontsize=12, fontweight="bold",
               bbox=dict(boxstyle="round,pad=0.6", facecolor="white",
                        edgecolor="#1a5276", linewidth=2.5, alpha=0.98),
               arrowprops=dict(arrowstyle="->", lw=2, color="#1a5276",
                             connectionstyle="arc3,rad=0.1"),
               zorder=10)
    
    # GOAL (Carnegie Hall)
    ax.scatter(ch_lon, ch_lat, s=1400, c="#e74c3c", edgecolor="#922b21",
              linewidth=5, marker="*", zorder=9)
    ax.annotate("GOAL (sᵍ)\nCarnegie Hall\n57th & 7th",
               xy=(ch_lon, ch_lat), xytext=(ch_lon - 0.0015, ch_lat + 0.002),
               ha="right", va="bottom",
               fontsize=12, fontweight="bold",
               bbox=dict(boxstyle="round,pad=0.6", facecolor="white",
                        edgecolor="#922b21", linewidth=2.5, alpha=0.98),
               arrowprops=dict(arrowstyle="->", lw=2, color="#922b21",
                             connectionstyle="arc3,rad=0.1"),
               zorder=10)
    
    # Set bounds
    ax.set_xlim(lon_min, lon_max)
    ax.set_ylim(lat_min, lat_max)
    ax.set_aspect("equal")
    
    # Labels
    ax.set_xlabel("Longitude", fontsize=15, fontweight="bold", color="#2c3e50")
    ax.set_ylabel("Latitude", fontsize=15, fontweight="bold", color="#2c3e50")
    
    # Title
    num_cameras = len(camera_coords) if len(camera_coords) > 0 else 0
    num_intersections = len(intersections) if intersections is not None else 0
    ax.set_title(
        f"Voronoi Tessellation: Camera Coverage Zones\n"
        f"{num_intersections} Intersections | "
        f"{num_cameras} Camera Zones",
        fontsize=17, fontweight="bold", pad=20
    )
    
    # North arrow
    ax.annotate("", xy=(-73.969, 40.771), xytext=(-73.969, 40.766),
               arrowprops=dict(arrowstyle="->", lw=6, color="#2c3e50"))
    ax.text(-73.969, 40.7722, "N", ha="center", va="bottom",
           fontsize=24, fontweight="bold", color="#2c3e50")
    
    # Legend
    legend_elements = []
    if intersections is not None:
        legend_elements.append(
            plt.Line2D([0], [0], marker="o", color="w", markerfacecolor="white",
                      markeredgecolor="#c0392b", markeredgewidth=2.5, markersize=12,
                      label=f"{len(intersections)} intersection nodes")
        )
    if len(camera_coords) > 0:
        legend_elements.append(
            plt.Line2D([0], [0], marker="^", color="w", markerfacecolor="#27ae60",
                      markeredgecolor="#196f3d", markeredgewidth=3, markersize=14,
                      label=f"{len(camera_coords)} cameras")
        )
    legend_elements.append(
        plt.Line2D([0], [0], color="#ffd700", linewidth=3, linestyle="-",
                  label="Voronoi boundaries")
    )
    
    if len(legend_elements) > 0:
        ax.legend(handles=legend_elements, loc="center left", bbox_to_anchor=(1.02, 0.5),
                 fontsize=13, framealpha=0.97, title="State Space Components",
                 title_fontsize=14, edgecolor="#34495e", fancybox=True, shadow=True)
    
    # Info box
    num_cameras = len(camera_coords) if len(camera_coords) > 0 else 0
    num_intersections = len(intersections) if intersections is not None else 0
    info = (
        f"VORONOI ZONES:\n"
        f"Total zones: {len(zones)}\n"
        f"Camera zones: {num_cameras}\n"
        f"Intersections: {num_intersections}\n\n"
        f"Voronoi assigns features:\n"
        f"Each intersection inherits\n"
        f"features from nearest camera"
    )
    ax.text(0.02, 0.98, info, transform=ax.transAxes,
           fontsize=11, va="top", ha="left",
           bbox=dict(boxstyle="round,pad=0.8", facecolor="#f8f9f9",
                    edgecolor="#34495e", linewidth=2.5, alpha=0.97),
           family="monospace", color="#2c3e50")
    
    ax.grid(True, alpha=0.1, linewidth=0.6, color="#95a5a6", linestyle=":")
    
    plt.tight_layout(rect=[0, 0, 0.95, 1])  # Leave space on right for legend
    
    if output_path:
        plt.savefig(output_path, dpi=dpi, bbox_inches="tight", facecolor="white")
        LOGGER.info("Saved Voronoi map to %s", output_path)
    else:
        plt.show()
    
    plt.close(fig)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    
    # Load data
    zones = load_zones(args.zones)
    cameras = load_cameras(args.manifest)
    
    streets = None
    if args.dcm_shapefile and args.dcm_shapefile.exists():
        streets = load_streets(args.dcm_shapefile, args.bounds)
    
    intersections = load_intersections(args.intersections)
    
    # Create visualization
    create_voronoi_visualization(
        zones=zones,
        cameras=cameras,
        streets=streets,
        intersections=intersections,
        bounds=args.bounds,
        output_path=args.output,
        figsize=tuple(args.figsize),
        dpi=args.dpi,
    )
    
    print(f"\n{'=' * 70}")
    print("VORONOI TESSELLATION MAP GENERATED")
    print(f"{'=' * 70}")
    print(f"\nOutput: {args.output}")
    print(f"Zones: {len(zones)}")
    print(f"Cameras: {len(cameras)}")
    if intersections is not None:
        print(f"Intersections: {len(intersections)}")
    if streets is not None:
        print(f"Street segments: {len(streets)}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

