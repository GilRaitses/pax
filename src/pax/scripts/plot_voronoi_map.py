"""Render Voronoi tessellations over the Midtown corridor map."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--zones",
        type=Path,
        default=Path("data/voronoi_zones.geojson"),
        help="Voronoi polygons GeoJSON",
    )
    parser.add_argument(
        "--cameras",
        type=Path,
        default=Path("data/corridor_cameras.geojson"),
        help="Camera points GeoJSON",
    )
    parser.add_argument(
        "--corridor",
        type=Path,
        default=Path("data/corridor_polygon.geojson"),
        help="Corridor boundary GeoJSON",
    )
    parser.add_argument(
        "--streets",
        type=Path,
        default=Path("docs/data/dcm/DCM_StreetCenterLine.shp"),
        help="Street centerline shapefile",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/voronoi_map.png"),
        help="Output PNG path",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="Figure DPI",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level",
    )
    return parser


def load_data(zones_path: Path, cameras_path: Path, corridor_path: Path, streets_path: Path):
    zones = gpd.read_file(zones_path)
    cameras = gpd.read_file(cameras_path)
    corridor = gpd.read_file(corridor_path)
    streets = gpd.read_file(streets_path)

    zones = zones.to_crs(epsg=4326)
    cameras = cameras.to_crs(epsg=4326)
    corridor = corridor.to_crs(epsg=4326)
    streets = streets.to_crs(epsg=4326)

    corridor_geom = corridor.geometry.iloc[0]
    streets = gpd.clip(streets, corridor_geom.buffer(0.01))

    return zones, cameras, corridor, streets


def style_plot(zones: gpd.GeoDataFrame, cameras: gpd.GeoDataFrame, corridor: gpd.GeoDataFrame, streets: gpd.GeoDataFrame, output: Path, dpi: int) -> None:
    plt.style.use("seaborn-v0_8-white")
    fig, ax = plt.subplots(figsize=(10, 14))

    streets.plot(ax=ax, color="#c7c7c7", linewidth=0.5)
    corridor.boundary.plot(ax=ax, color="#2f4f4f", linewidth=1.5)

    zones = zones.copy()
    zones["zone_idx"] = range(len(zones))
    zones.plot(
        ax=ax,
        column="zone_idx",
        cmap="tab20",
        edgecolor="#f0f0f0",
        linewidth=0.5,
        alpha=0.6,
    )

    cameras.plot(ax=ax, color="#003f5c", markersize=12, edgecolor="white", linewidth=0.3)

    for _, row in cameras.iterrows():
        ax.annotate(
            text=row.get("name", ""),
            xy=(row.geometry.x, row.geometry.y),
            xytext=(3, 3),
            textcoords="offset points",
            fontsize=6,
            color="#1f1f1f",
        )

    ax.set_title(
        "Midtown Corridor Camera Voronoi Zones\nLexington Ave to 9th Ave, 34th St to 66th St",
        fontsize=14,
        weight="bold",
    )
    ax.set_axis_off()

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(level=args.log_level.upper(), format="%(levelname)s: %(message)s")

    zones, cameras, corridor, streets = load_data(args.zones, args.cameras, args.corridor, args.streets)

    LOGGER.info("Rendering Voronoi map with %d zones and %d cameras", len(zones), len(cameras))
    style_plot(zones, cameras, corridor, streets, args.output, args.dpi)
    LOGGER.info("Saved map to %s", args.output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
