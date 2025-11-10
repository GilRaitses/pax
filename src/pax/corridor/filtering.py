"""Filter NYCTMC cameras to the Lexington–9th Ave corridor using street data."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, Polygon, box

LOGGER = logging.getLogger(__name__)

# Strings that should exclude a camera even if it falls inside the polygon.
EXCLUDED_NAME_TOKENS = (
    " 1 AVE",
    "1 AVE",
    " 2 AVE",
    "2 AVE",
    "FDR",
    "EAST RIVER",
    "QUEENSBORO",
    "QUEENS",
    "ED RIVER",
    "RFK",
    "QBB",
    " 10 AVE",
    " 11 AVE",
    " 12 AVE",
    " WEST SIDE HWY",
    " WEST STREET",
)


@dataclass(slots=True)
class CorridorBounds:
    """Axis-aligned bounds derived from street centerlines."""

    south_street: int
    north_street: int
    east_avenue: str
    west_avenue: str
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    buffer: float = 0.0005

    def polygon(self) -> Polygon:
        """Return a shapely polygon representing the corridor."""

        return box(self.lon_min - self.buffer, self.lat_min - self.buffer, self.lon_max + self.buffer, self.lat_max + self.buffer)


def _load_dcm(dcm_path: Path) -> gpd.GeoDataFrame:
    LOGGER.info("Loading DCM street centerlines: %s", dcm_path)
    dcm = gpd.read_file(dcm_path)
    if dcm.crs is None or dcm.crs.to_epsg() != 4326:
        LOGGER.info("Reprojecting DCM to EPSG:4326")
        dcm = dcm.to_crs(epsg=4326)
    if "Street_NM" not in dcm.columns:
        raise KeyError("Expected 'Street_NM' column in DCM shapefile")
    if "Borough" in dcm.columns:
        dcm = dcm[dcm["Borough"].str.upper() == "MANHATTAN"].copy()
    return dcm


def _subset_by_pattern(dcm: gpd.GeoDataFrame, pattern: str) -> gpd.GeoDataFrame:
    subset = dcm[dcm["Street_NM"].str.contains(pattern, case=False, na=False, regex=True)]
    if subset.empty:
        raise ValueError(f"Could not find street names matching pattern '{pattern}'")
    return subset


def derive_corridor_bounds(
    dcm_path: Path,
    south_street: int = 34,
    north_street: int = 66,
    east_avenue: str = "Lexington Avenue",
    west_avenue: str = "9 Avenue",
    pad_degrees: float = 0.0007,
) -> CorridorBounds:
    """Compute corridor bounds from street names."""

    dcm = _load_dcm(dcm_path)

    street_pattern = rf"^(?:East|West)\s+{south_street}\s+Street$"
    south_subset = _subset_by_pattern(dcm, street_pattern)
    north_subset = _subset_by_pattern(dcm, rf"^(?:East|West)\s+{north_street}\s+Street$")

    lat_min = float(min(south_subset.total_bounds[1], north_subset.total_bounds[1]) - pad_degrees)
    lat_max = float(max(south_subset.total_bounds[3], north_subset.total_bounds[3]) + pad_degrees)

    avenue_pattern = rf"^{re.escape(east_avenue)}$"
    east_subset = _subset_by_pattern(dcm, avenue_pattern)
    west_subset = _subset_by_pattern(dcm, rf"^{re.escape(west_avenue)}$")

    # Restrict avenues to the street span we care about
    east_bounds_df = east_subset.bounds
    east_subset = east_subset[
        (east_bounds_df["maxy"] >= lat_min) & (east_bounds_df["miny"] <= lat_max)
    ]
    if east_subset.empty:
        raise ValueError("East avenue filter left no segments; check inputs")
    west_bounds_df = west_subset.bounds
    west_subset = west_subset[
        (west_bounds_df["maxy"] >= lat_min) & (west_bounds_df["miny"] <= lat_max)
    ]
    if west_subset.empty:
        raise ValueError("West avenue filter left no segments; check inputs")

    east_bounds = east_subset.total_bounds
    west_bounds = west_subset.total_bounds

    # east_bounds[2] is the maximum longitude (least negative) among Lexington Avenue segments.
    lon_max = float(max(east_bounds[0], east_bounds[2]) + pad_degrees)
    # west_bounds[0] is the minimum longitude (most negative) along 9th Ave.
    lon_min = float(min(west_bounds[0], west_bounds[2]) - pad_degrees)

    LOGGER.info(
        "Derived corridor bounds lat=[%.6f, %.6f], lon=[%.6f, %.6f]",
        lat_min,
        lat_max,
        lon_min,
        lon_max,
    )

    return CorridorBounds(
        south_street=south_street,
        north_street=north_street,
        east_avenue=east_avenue,
        west_avenue=west_avenue,
        lat_min=lat_min,
        lat_max=lat_max,
        lon_min=lon_min,
        lon_max=lon_max,
        buffer=pad_degrees,
    )


def _name_is_excluded(name: str) -> bool:
    upper = name.upper()
    return any(token in upper for token in EXCLUDED_NAME_TOKENS)


def filter_cameras_to_corridor(
    cameras: Iterable[dict[str, object]],
    corridor_bounds: CorridorBounds,
) -> pd.DataFrame:
    """Return cameras that fall within the derived corridor polygon."""

    records: list[dict[str, object]] = []
    for cam in cameras:
        try:
            lat = float(cam.get("latitude", 0.0))
            lon = float(cam.get("longitude", 0.0))
        except (TypeError, ValueError):
            LOGGER.debug("Skipping camera with invalid coordinates: %s", cam)
            continue

        name = str(cam.get("name", "")).strip()
        if _name_is_excluded(name):
            LOGGER.debug("Skipping %s due to name exclusion", name)
            continue

        area = str(cam.get("area", "")).strip()
        if area and area.upper() != "MANHATTAN":
            LOGGER.debug("Skipping %s because area=%s", name, area)
            continue

        records.append(
            {
                "id": cam.get("id"),
                "name": name,
                "latitude": lat,
                "longitude": lon,
                "area": area,
                "source": cam,
            }
        )

    if not records:
        LOGGER.warning("No cameras available after initial validation")
        return pd.DataFrame(columns=["id", "name", "latitude", "longitude", "area", "geometry"])

    df = pd.DataFrame.from_records(records)
    geometry = [Point(lon, lat) for lon, lat in zip(df["longitude"], df["latitude"])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

    polygon = corridor_bounds.polygon()
    LOGGER.info("Filtering cameras with polygon bounds: %s", polygon.bounds)
    mask = gdf.within(polygon) | gdf.touches(polygon)
    filtered = gdf.loc[mask].copy()

    LOGGER.info("Selected %d cameras inside corridor (out of %d)", len(filtered), len(gdf))

    filtered.sort_values("latitude", inplace=True)
    filtered.reset_index(drop=True, inplace=True)
    return filtered


__all__ = ["CorridorBounds", "derive_corridor_bounds", "filter_cameras_to_corridor"]
