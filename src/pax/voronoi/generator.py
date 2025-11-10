"""Generate Voronoi zones for the Lexington–9th corridor."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import numpy as np
from scipy.spatial import Voronoi
from shapely.geometry import MultiPolygon, Point, Polygon
from shapely.ops import unary_union

from ..corridor import CorridorBounds

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class CorridorVoronoiResult:
    """Container for Voronoi results."""

    zones: gpd.GeoDataFrame
    walkable_area: Polygon | MultiPolygon
    bounds: CorridorBounds


def _build_walkable_area(
    dcm_path: Path,
    bounds: CorridorBounds,
    street_buffer_m: float = 18.0,
) -> Polygon | MultiPolygon:
    LOGGER.info("Building walkable area from DCM shapefile")
    dcm = gpd.read_file(dcm_path)
    if dcm.crs is None or dcm.crs.to_epsg() != 4326:
        dcm = dcm.to_crs(epsg=4326)
    if "Borough" in dcm.columns:
        dcm = dcm[dcm["Borough"].str.upper() == "MANHATTAN"].copy()

    corridor = dcm.cx[bounds.lon_min:bounds.lon_max, bounds.lat_min:bounds.lat_max]
    if corridor.empty:
        raise ValueError("No street centerlines found within corridor bounds")

    metric = corridor.to_crs(epsg=3857)
    buffered = metric.buffer(street_buffer_m)
    union = unary_union(buffered)
    geoseries = gpd.GeoSeries([union], crs="EPSG:3857").to_crs(epsg=4326)
    walkable = geoseries.iloc[0]
    LOGGER.info("Walkable area computed with buffer %.1fm", street_buffer_m)
    return walkable


def _voronoi_polygon(vor: Voronoi, index: int, clip_polygon: Polygon) -> Polygon:
    region_idx = vor.point_region[index]
    region = vor.regions[region_idx]
    if not region or -1 in region:
        return Polygon()
    vertices = vor.vertices[region]
    polygon = Polygon(vertices)
    clipped = polygon.intersection(clip_polygon)
    if clipped.is_empty:
        return Polygon()
    if isinstance(clipped, (MultiPolygon,)):
        clipped = max(clipped.geoms, key=lambda geom: geom.area)
    return clipped


def _fallback_polygon(point: Point, clip_polygon: Polygon, meters: float = 60.0) -> Polygon:
    # Approximate degree buffer using meters (~111_320 meters per degree)
    degree_buffer = meters / 111_320
    buffered = point.buffer(degree_buffer)
    clipped = buffered.intersection(clip_polygon)
    if isinstance(clipped, MultiPolygon):
        clipped = max(clipped.geoms, key=lambda geom: geom.area)
    return clipped


def generate_corridor_voronoi(
    cameras: gpd.GeoDataFrame,
    bounds: CorridorBounds,
    dcm_path: Path,
    street_buffer_m: float = 18.0,
) -> CorridorVoronoiResult:
    """Compute Voronoi zones and clip them to the street network."""

    if cameras.empty:
        raise ValueError("No cameras provided for Voronoi computation")

    cameras_sorted = cameras.sort_values("latitude").reset_index(drop=True)
    points = cameras_sorted[["longitude", "latitude"]].to_numpy()

    LOGGER.info("Computing Voronoi diagram for %d cameras", len(points))
    vor = Voronoi(points)

    clip_polygon = bounds.polygon()
    walkable_area = _build_walkable_area(dcm_path, bounds, street_buffer_m=street_buffer_m)

    geometries = []
    records = []

    for idx, row in cameras_sorted.iterrows():
        point = Point(points[idx])
        polygon = _voronoi_polygon(vor, idx, clip_polygon)
        if polygon.is_empty:
            LOGGER.debug("Camera %s has infinite region; using fallback", row["name"])
            polygon = _fallback_polygon(point, clip_polygon)

        clipped = polygon.intersection(walkable_area)
        if clipped.is_empty:
            clipped = polygon
        if isinstance(clipped, MultiPolygon):
            clipped = max(clipped.geoms, key=lambda geom: geom.area)

        if clipped.is_empty:
            clipped = _fallback_polygon(point, clip_polygon, meters=25.0)

        geometries.append(clipped)
        records.append(
            {
                "camera_id": row["id"],
                "camera_name": row["name"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "area": row.get("area", ""),
                "priority": row.get("priority", ""),
            }
        )

    zones = gpd.GeoDataFrame(records, geometry=geometries, crs="EPSG:4326")
    zones["zone_area_m2"] = zones.to_crs(epsg=3857).area
    zones["num_vertices"] = zones.geometry.apply(lambda geom: len(geom.exterior.coords) if isinstance(geom, Polygon) else 0)
    zones["coordinates_lonlat"] = zones.geometry.apply(
        lambda geom: [list(coord) for coord in geom.exterior.coords]
    )

    return CorridorVoronoiResult(zones=zones, walkable_area=walkable_area, bounds=bounds)


__all__ = ["CorridorVoronoiResult", "generate_corridor_voronoi"]
