"""Construct Voronoi zones for corridor cameras and export GeoJSON/Parquet."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
import yaml
from scipy.spatial import Voronoi
from shapely.geometry import MultiPoint, Point, Polygon
from shapely.ops import unary_union

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/corridor_cameras.yaml"),
        help="Camera manifest produced by build_corridor_manifest",
    )
    parser.add_argument(
        "--corridor",
        type=Path,
        default=Path("data/corridor_polygon.geojson"),
        help="GeoJSON polygon that defines the corridor boundary",
    )
    parser.add_argument(
        "--street-centerlines",
        type=Path,
        default=Path("docs/data/dcm/DCM_StreetCenterLine.shp"),
        help="NYC Planning DCM street centerline shapefile",
    )
    parser.add_argument(
        "--output-zones",
        type=Path,
        default=Path("data/voronoi_zones.geojson"),
        help="Output path for Voronoi polygons (GeoJSON)",
    )
    parser.add_argument(
        "--output-parquet",
        type=Path,
        default=Path("data/voronoi_zones.parquet"),
        help="Output path for Voronoi polygons (Parquet)",
    )
    parser.add_argument(
        "--output-cameras",
        type=Path,
        default=Path("data/corridor_cameras.geojson"),
        help="GeoJSON export for camera points",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level",
    )
    return parser


def load_manifest(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")

    LOGGER.info("Loading cameras from %s", path)
    if path.suffix.lower() in {".yaml", ".yml"}:
        manifest = yaml.safe_load(path.read_text())
        cameras = manifest.get("cameras", []) if isinstance(manifest, dict) else manifest
    elif path.suffix.lower() == ".json":
        cameras = json.loads(path.read_text())
    else:
        raise ValueError(f"Unsupported manifest extension: {path.suffix}")

    cleaned: list[dict[str, Any]] = []
    for cam in cameras:
        if cam.get("latitude") is None or cam.get("longitude") is None:
            continue
        cleaned.append(
            {
                "id": cam.get("id"),
                "name": cam.get("name", ""),
                "lat": float(cam["latitude"]),
                "lon": float(cam["longitude"]),
            }
        )

    LOGGER.info("Loaded %d cameras", len(cleaned))
    return cleaned


def voronoi_finite_polygons_2d(vor: Voronoi, radius: float | None = None) -> tuple[list[list[int]], np.ndarray]:
    """Reconstruct infinite Voronoi regions into finite polygons.

    Adapted from: https://gist.github.com/pv/8036995
    """

    if vor.points.shape[1] != 2:
        raise ValueError("Requires 2D input")

    new_regions: list[list[int]] = []
    new_vertices = vor.vertices.tolist()

    center = vor.points.mean(axis=0)
    if radius is None:
        radius = vor.points.ptp().max()

    # Map ridge vertices to point pairs
    all_ridges: dict[int, list[tuple[int, int]]] = {}
    for (p1, p2), (v1, v2) in zip(vor.ridge_points, vor.ridge_vertices):
        all_ridges.setdefault(p1, []).append((p2, v1, v2))
        all_ridges.setdefault(p2, []).append((p1, v1, v2))

    for point_idx, region_idx in enumerate(vor.point_region):
        vertices = vor.regions[region_idx]
        if all(v >= 0 for v in vertices):
            new_regions.append(vertices)
            continue

        ridges = all_ridges[point_idx]
        region: list[int] = [v for v in vertices if v >= 0]

        for p2, v1, v2 in ridges:
            if v2 < 0 or v1 < 0:
                v = v1 if v1 >= 0 else v2
                tangent = vor.points[p2] - vor.points[point_idx]
                tangent /= np.linalg.norm(tangent)
                normal = np.array([-tangent[1], tangent[0]])
                midpoint = vor.points[[point_idx, p2]].mean(axis=0)
                direction = np.sign(np.dot(midpoint - center, normal)) * normal
                far_point = vor.vertices[v] + direction * radius
                new_vertices.append(far_point.tolist())
                region.append(len(new_vertices) - 1)

        # order region counterclockwise
        region_arr = np.asarray([new_vertices[v] for v in region])
        centroid = region_arr.mean(axis=0)
        angles = np.arctan2(region_arr[:, 1] - centroid[1], region_arr[:, 0] - centroid[0])
        region = [v for _, v in sorted(zip(angles, region))]
        new_regions.append(region)

    return new_regions, np.asarray(new_vertices)


def densify_street_union(centerlines: gpd.GeoDataFrame) -> gpd.GeoSeries:
    # Combine street segments into a single buffered geometry for clipping guard-rails
    unary = unary_union(centerlines.geometry)
    return gpd.GeoSeries([unary], crs=centerlines.crs)


def generate_voronoi(
    cameras_gdf: gpd.GeoDataFrame,
    corridor_polygon: gpd.GeoSeries,
) -> gpd.GeoDataFrame:
    LOGGER.info("Generating Voronoi diagram in EPSG:3857")
    metric_points = cameras_gdf.to_crs(epsg=3857)
    metric_polygon = corridor_polygon.to_crs(epsg=3857).geometry.iloc[0]

    coords = np.column_stack((metric_points.geometry.x, metric_points.geometry.y))
    vor = Voronoi(coords)
    regions, vertices = voronoi_finite_polygons_2d(vor)

    polygons: list[Polygon] = []
    for region in regions:
        polygon = Polygon(vertices[region])
        polygon = polygon.intersection(metric_polygon)
        if polygon.is_empty:
            polygon = Polygon()
        polygons.append(polygon)

    zones_metric = gpd.GeoDataFrame(cameras_gdf.drop(columns="geometry"), geometry=polygons, crs="EPSG:3857")
    zones_geo = zones_metric.to_crs(epsg=4326)
    zones_geo["area_sq_m"] = zones_metric.area
    return zones_geo


def export_outputs(
    zones: gpd.GeoDataFrame,
    cameras: gpd.GeoDataFrame,
    output_zones: Path,
    output_parquet: Path,
    output_cameras: Path,
) -> None:
    output_zones.parent.mkdir(parents=True, exist_ok=True)
    zones.to_file(output_zones, driver="GeoJSON")
    LOGGER.info("Wrote zones GeoJSON to %s", output_zones)

    output_parquet.parent.mkdir(parents=True, exist_ok=True)
    zones.to_parquet(output_parquet, index=False)
    LOGGER.info("Wrote zones Parquet to %s", output_parquet)

    output_cameras.parent.mkdir(parents=True, exist_ok=True)
    cameras.to_file(output_cameras, driver="GeoJSON")
    LOGGER.info("Wrote cameras GeoJSON to %s", output_cameras)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(level=args.log_level.upper(), format="%(levelname)s: %(message)s")

    cameras = load_manifest(args.manifest)
    if not cameras:
        LOGGER.error("No cameras found in manifest")
        return 1

    cameras_gdf = gpd.GeoDataFrame(
        cameras,
        geometry=gpd.points_from_xy([c["lon"] for c in cameras], [c["lat"] for c in cameras]),
        crs="EPSG:4326",
    )

    corridor = gpd.read_file(args.corridor)
    if corridor.empty:
        LOGGER.error("Corridor polygon is empty: %s", args.corridor)
        return 1

    zones = generate_voronoi(cameras_gdf, corridor)
    LOGGER.info("Generated %d Voronoi zones", len(zones))

    export_outputs(zones, cameras_gdf, args.output_zones, args.output_parquet, args.output_cameras)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
