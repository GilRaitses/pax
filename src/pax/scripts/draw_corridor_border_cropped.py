"""Draw corridor border on Voronoi map - aligned grid version (no rotation)."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from scipy.spatial import Voronoi

LOGGER = logging.getLogger(__name__)


def load_intersections(path: Path) -> dict:
    """Load intersection data."""
    with open(path) as f:
        return json.load(f)


def load_cameras(path: Path) -> list[dict]:
    """Load camera data."""
    with open(path) as f:
        return json.load(f)


def load_streets(path: Path) -> gpd.GeoDataFrame:
    """Load street centerlines."""
    streets = gpd.read_file(path)
    if streets.crs != "EPSG:4326":
        streets = streets.to_crs(epsg=4326)
    return streets[streets["Borough"] == "Manhattan"]


def find_corridor_corners_from_shapefile(streets: gpd.GeoDataFrame) -> dict[str, tuple[float, float]]:
    """Find all 4 corners by computing intersections from shapefile."""
    corners = {}
    
    # Filter to corridor area
    corridor = streets.cx[-73.995:-73.965, 40.745:40.770]
    
    # Find all geometric intersections
    for i, row1 in corridor.iterrows():
        for j, row2 in corridor.iterrows():
            if i >= j:
                continue
            
            if row1.geometry.intersects(row2.geometry):
                inter = row1.geometry.intersection(row2.geometry)
                if inter.geom_type == "Point":
                    lon, lat = inter.x, inter.y
                    name1 = str(row1.get('Street_NM', '')).lower()
                    name2 = str(row2.get('Street_NM', '')).lower()
                    
                    # Check for corners - use 61st Street for north border
                    has_8 = '8 avenue' in name1 or '8 avenue' in name2
                    has_lex = 'lexington' in name1 or 'lexington' in name2
                    has_cpw = 'central park west' in name1 or 'central park west' in name2
                    has_61 = '61' in name1 or '61' in name2
                    has_west_40 = 'west 40' in name1 or 'west 40' in name2
                    has_east_40 = 'east 40' in name1 or 'east 40' in name2
                    
                    # Find actual corners
                    if has_cpw and has_61 and "NW" not in corners:
                        corners["NW"] = (lon, lat)
                        LOGGER.info("Found NW: (%.6f, %.6f) from %s x %s", lon, lat, name1, name2)
                    elif has_lex and has_61 and "NE" not in corners:
                        corners["NE"] = (lon, lat)
                        LOGGER.info("Found NE: (%.6f, %.6f) from %s x %s", lon, lat, name1, name2)
                    elif has_lex and has_east_40 and "SE" not in corners:
                        corners["SE"] = (lon, lat)
                        LOGGER.info("Found SE: (%.6f, %.6f) from %s x %s", lon, lat, name1, name2)
                    elif has_8 and has_west_40 and "SW" not in corners:
                        corners["SW"] = (lon, lat)
                        LOGGER.info("Found SW: (%.6f, %.6f) from %s x %s", lon, lat, name1, name2)
    
    return corners


def draw_corridor_border_aligned(
    corners: dict[str, tuple[float, float]],
    cameras: list[dict],
    intersections: np.ndarray,
    streets: gpd.GeoDataFrame,
    output: Path,
) -> None:
    """Draw the Voronoi map with corridor border - aligned grid."""
    
    if len(corners) != 4:
        raise ValueError(f"Need all 4 corners, found {len(corners)}: {list(corners.keys())}")
    
    # Use corridor bounds from corners
    lons = [c[0] for c in corners.values()]
    lats = [c[1] for c in corners.values()]
    lon_min, lon_max = min(lons) - 0.001, max(lons) + 0.001
    lat_min, lat_max = min(lats) - 0.001, max(lats) + 0.001
    
    # Create figure
    fig, ax = plt.subplots(figsize=(20, 16), dpi=300)
    
    # Filter streets to problem space
    problem_streets = streets.cx[lon_min:lon_max, lat_min:lat_max]
    problem_streets.plot(ax=ax, color="#2c3e50", linewidth=1.8, alpha=0.7, zorder=2)
    
    # Plot Voronoi tessellation
    camera_coords = np.array([[float(cam["longitude"]), float(cam["latitude"])] for cam in cameras])
    vor = Voronoi(camera_coords)
    buffer = 0.001
    for simplex in vor.ridge_vertices:
        simplex = np.asarray(simplex)
        if np.all(simplex >= 0):
            verts = vor.vertices[simplex]
            if (
                np.all(lat_min - buffer <= verts[:, 1])
                and np.all(verts[:, 1] <= lat_max + buffer)
                and np.all(lon_min - buffer <= verts[:, 0])
                and np.all(verts[:, 0] <= lon_max + buffer)
            ):
                for width, alpha in [(12, 0.05), (10, 0.08), (8, 0.1), (6, 0.12), (4, 0.15), (2, 0.18)]:
                    ax.plot(
                        verts[:, 0],
                        verts[:, 1],
                        color="#ffd700",
                        linewidth=width,
                        alpha=alpha,
                        zorder=3,
                        linestyle="-",
                        solid_capstyle="round",
                    )
    
    # Draw corridor perimeter: NW -> NE -> SE -> SW -> NW
    perimeter = [
        corners["NW"],
        corners["NE"],
        corners["SE"],
        corners["SW"],
        corners["NW"],  # Close the loop
    ]
    perimeter_array = np.array(perimeter)
    
    ax.plot(
        perimeter_array[:, 0],
        perimeter_array[:, 1],
        color="#e74c3c",
        linewidth=4,
        linestyle="-",
        marker="o",
        markersize=8,
        markerfacecolor="#e74c3c",
        markeredgecolor="#c0392b",
        markeredgewidth=2,
        zorder=8,
        label="Constrained space (40th-61st, Lex-CPW)",
    )
    
    LOGGER.info("Drew perimeter: NW (%.6f, %.6f) -> NE (%.6f, %.6f) -> SE (%.6f, %.6f) -> SW (%.6f, %.6f)",
                corners["NW"][0], corners["NW"][1],
                corners["NE"][0], corners["NE"][1],
                corners["SE"][0], corners["SE"][1],
                corners["SW"][0], corners["SW"][1])
    
    # Plot intersection nodes
    ax.scatter(
        intersections[:, 0],
        intersections[:, 1],
        s=55,
        c="white",
        edgecolor="#e74c3c",
        linewidth=1.5,
        zorder=6,
        alpha=0.95,
        label=f"{len(intersections)} intersection nodes",
    )
    
    # Plot cameras
    ax.scatter(
        camera_coords[:, 0],
        camera_coords[:, 1],
        s=180,
        c="#2ecc71",
        edgecolor="#27ae60",
        linewidth=2.5,
        zorder=7,
        alpha=0.95,
        label=f"{len(cameras)} cameras",
        marker="^",
    )
    
    # Plot START and GOAL
    gc_lon, gc_lat = -73.9772, 40.7527
    ch_lon, ch_lat = -73.9806, 40.7651
    
    ax.scatter(gc_lon, gc_lat, s=1400, c="#3498db", edgecolor="#1a5276", linewidth=5, marker="*", zorder=9)
    ax.annotate(
        "START (s₀)",
        xy=(gc_lon, gc_lat),
        xytext=(gc_lon + 0.002, gc_lat - 0.003),
        ha="left",
        va="top",
        fontsize=11,
        weight="bold",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="#3498db", linewidth=2),
        arrowprops=dict(arrowstyle="->", lw=2, color="#3498db"),
        zorder=10,
    )
    ax.text(gc_lon, gc_lat - 0.005, "Grand Central\n42nd & Park", 
            ha="center", va="top", fontsize=9, style="italic")
    
    ax.scatter(ch_lon, ch_lat, s=1400, c="#e74c3c", edgecolor="#922b21", linewidth=5, marker="*", zorder=9)
    ax.annotate(
        "GOAL (sᵍ)",
        xy=(ch_lon, ch_lat),
        xytext=(ch_lon - 0.002, ch_lat + 0.003),
        ha="right",
        va="bottom",
        fontsize=11,
        weight="bold",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="#e74c3c", linewidth=2),
        arrowprops=dict(arrowstyle="->", lw=2, color="#e74c3c"),
        zorder=10,
    )
    ax.text(ch_lon, ch_lat + 0.005, "Carnegie Hall\n57th & 7th", 
            ha="center", va="bottom", fontsize=9, style="italic")
    
    # Add compass - positioned in top right
    ax.annotate(
        "N",
        xy=(lon_max - 0.001, lat_max - 0.001),
        fontsize=28,
        weight="bold",
        ha="right",
        va="top",
    )
    
    # Set axis labels and title
    ax.set_xlabel("Longitude", fontsize=14, weight="bold")
    ax.set_ylabel("Latitude", fontsize=14, weight="bold")
    ax.set_xlim(lon_min, lon_max)
    ax.set_ylim(lat_min, lat_max)
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3, linestyle="--", linewidth=0.5)
    ax.legend(loc="center left", framealpha=0.95, fontsize=11, bbox_to_anchor=(1.02, 0.5))
    
    # Add text box
    textstr = (
        "STATE SPACE:\n"
        f"Total nodes: {len(intersections)}\n"
        f"Camera zones: {len(cameras)}\n"
        "Constrained: 40th-61st, Lex-CPW\n"
        "Extended corridor for Pareto\n"
        "\n"
        "Voronoi assigns features:\n"
        "Each intersection inherits\n"
        "features from nearest camera"
    )
    ax.text(
        0.02,
        0.98,
        textstr,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.9, edgecolor="black", linewidth=1.5),
    )
    
    plt.tight_layout()
    plt.savefig(output, dpi=300, bbox_inches="tight")
    plt.close()
    LOGGER.info("Saved aligned map to %s", output)


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--intersections",
        type=Path,
        default=Path("data/geojson/intersections.json"),
        help="Path to intersection data JSON",
    )
    parser.add_argument(
        "--cameras",
        type=Path,
        default=Path("data/manifests/corridor_88_cameras.json"),
        help="Path to camera data JSON",
    )
    parser.add_argument(
        "--streets",
        type=Path,
        default=Path("data/shapefiles/dcm/DCM_StreetCenterLine.shp"),
        help="Path to DCM street centerline shapefile",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/voronoi_tessellation_aligned.png"),
        help="Output path for the map",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )
    
    args = parser.parse_args(argv)
    
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(levelname)s: %(message)s",
    )
    
    # Load data
    LOGGER.info("Loading intersections from %s", args.intersections)
    intersections_data = load_intersections(args.intersections)
    intersections = np.array(intersections_data["coordinates"])
    LOGGER.info("Loaded %d intersections", len(intersections))
    
    LOGGER.info("Loading cameras from %s", args.cameras)
    cameras = load_cameras(args.cameras)
    LOGGER.info("Loaded %d cameras", len(cameras))
    
    LOGGER.info("Loading streets from %s", args.streets)
    streets = load_streets(args.streets)
    LOGGER.info("Loaded %d street segments", len(streets))
    
    # Find corridor corners from shapefile geometric intersections
    LOGGER.info("Finding corridor corners from shapefile geometric intersections...")
    corners = find_corridor_corners_from_shapefile(streets)
    LOGGER.info("Found corners: %s", list(corners.keys()))
    
    if len(corners) != 4:
        raise ValueError(f"Could not find all 4 corners. Found: {list(corners.keys())}")
    
    # Draw map
    draw_corridor_border_aligned(corners, cameras, intersections, streets, args.output)
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

