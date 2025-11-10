"""Generate corridor camera manifest using street network boundaries.

This script rebuilds the Midtown camera manifest using the NYC Planning
Digital City Map (DCM) street centerline data. Instead of latitude/longitude
thresholds, the corridor polygon is derived from buffered street centerlines
(Lexington Ave through 9th Ave, 34th St through 66th St).
"""

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
from shapely.geometry import Polygon
from shapely.ops import unary_union

LOGGER = logging.getLogger(__name__)

# Street naming variations to include inside the corridor
NORTH_SOUTH_STREETS = {
    "Lexington Avenue",
    "Park Avenue",
    "Madison Avenue",
    "5 Avenue",
    "Fifth Avenue",
    "Avenue Of The Americas",  # 6th Avenue official name
    "6 Avenue",
    "7 Avenue",
    "Broadway",
    "Dyer Avenue",
    "8 Avenue",
    "9 Avenue",
    "Columbus Avenue",  # ties into 9th north of 59th
}

# Strings that indicate the camera sits outside the desired corridor
DISALLOWED_TOKENS = [
    "1 Ave",
    "2 Ave",
    "York Ave",
    "FDR",
    "Ed Koch",
    "Queensboro",
    "Queens Mid",
    "11 Ave",
    "12 Ave",
    "West Street",
    "West St",
    "West Side Hwy",
]

EAST_WEST_START = 34
EAST_WEST_END = 66


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dcm",
        type=Path,
        default=Path("data/shapefiles/dcm/DCM_StreetCenterLine.shp"),
        help="Path to NYC Planning DCM StreetCenterLine shapefile",
    )
    parser.add_argument(
        "--cameras",
        type=Path,
        default=Path("docs/backup_20251105_150716/cameras_expanded_34th_66th.yaml"),
        help="Source camera list (YAML or JSON)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/manifests/corridor_cameras.yaml"),
        help="Output manifest path (YAML)",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("data/manifests/corridor_cameras.json"),
        help="Output JSON list of cameras",
    )
    parser.add_argument(
        "--export-corridor",
        type=Path,
        default=Path("data/geojson/corridor_polygon.geojson"),
        help="Optional GeoJSON export of the corridor polygon",
    )
    parser.add_argument(
        "--street-buffer-m",
        type=float,
        default=25.0,
        help="Buffer (meters) applied to avenue/ street centerlines",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level",
    )
    return parser


def load_cameras(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Camera source not found: {path}")

    LOGGER.info("Loading cameras from %s", path)
    if path.suffix.lower() in {".yaml", ".yml"}:
        data = yaml.safe_load(path.read_text())
        if isinstance(data, dict) and "cameras" in data:
            cameras = data["cameras"]
        elif isinstance(data, list):
            cameras = data
        else:
            raise ValueError("Unsupported YAML structure for cameras")
    elif path.suffix.lower() == ".json":
        cameras = json.loads(path.read_text())
    else:
        raise ValueError(f"Unsupported camera file extension: {path.suffix}")

    cleaned: list[dict[str, Any]] = []
    for cam in cameras:
        lat = cam.get("latitude")
        lon = cam.get("longitude")
        if lat is None or lon is None:
            continue
        cleaned.append(
            {
                "id": cam.get("id"),
                "name": cam.get("name", ""),
                "area": cam.get("area", ""),
                "latitude": float(lat),
                "longitude": float(lon),
                "source": path.name,
            }
        )

    LOGGER.info("Loaded %d cameras", len(cleaned))
    return cleaned


def filter_manhattan(dcm: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if "Borough" not in dcm.columns:
        return dcm
    return dcm[dcm["Borough"].str.lower() == "manhattan"].copy()


def select_north_south(dcm: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    return dcm[dcm["Street_NM"].isin(NORTH_SOUTH_STREETS)].copy()


def select_east_west(dcm: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    streets = []
    for number in range(EAST_WEST_START, EAST_WEST_END + 1):
        token = f" {number} Street"
        mask = dcm["Street_NM"].str.contains(token, case=False, na=False)
        if mask.any():
            streets.append(dcm[mask])
    if streets:
        return pd.concat(streets).drop_duplicates().copy()
    return dcm.iloc[0:0].copy()


def build_corridor_polygon(
    dcm_path: Path,
    street_buffer_m: float,
) -> Polygon:
    LOGGER.info("Reading DCM centerlines from %s", dcm_path)
    dcm = gpd.read_file(dcm_path)

    if dcm.crs is None:
        raise ValueError("DCM shapefile lacks CRS information")

    dcm = filter_manhattan(dcm)
    LOGGER.info("Manhattan segments: %d", len(dcm))

    ns = select_north_south(dcm)
    ew = select_east_west(dcm)

    LOGGER.info("Selected %d north/south and %d east/west segments", len(ns), len(ew))

    if ns.empty or ew.empty:
        raise ValueError("Failed to select corridor streets; check naming assumptions")

    combined = pd.concat([ns, ew]).drop_duplicates().copy()

    metric = combined.to_crs(epsg=3857)
    buffered = metric.buffer(street_buffer_m)

    # Merge into single polygon, convert back to geographic coordinates
    merged = gpd.GeoSeries(buffered, crs="EPSG:3857").unary_union

    if merged.is_empty:
        raise ValueError("Buffered street network produced an empty geometry")

    merged_geo = gpd.GeoSeries([merged], crs="EPSG:3857").to_crs(epsg=4326).iloc[0]

    if hasattr(merged_geo, "geoms"):
        # Take largest component to avoid stray fragments
        merged_geo = max(merged_geo.geoms, key=lambda geom: geom.area)

    if not isinstance(merged_geo, Polygon):
        # Fallback: take convex hull of merged geometry
        merged_geo = merged_geo.convex_hull

    LOGGER.info("Corridor polygon area (deg^2): %.6f", merged_geo.area)
    return merged_geo


def filter_cameras_by_polygon(
    cameras: list[dict[str, Any]],
    polygon: Polygon,
) -> gpd.GeoDataFrame:
    df = pd.DataFrame(cameras)
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["longitude"], df["latitude"]),
        crs="EPSG:4326",
    )

    LOGGER.info("Filtering cameras using corridor polygon")
    within_mask = gdf.within(polygon)
    gdf = gdf[within_mask].copy()
    LOGGER.info("%d cameras remain after spatial filter", len(gdf))

    if not gdf.empty:
        name_mask = ~gdf["name"].str.contains("|".join(DISALLOWED_TOKENS), case=False, na=False)
        filtered = gdf[name_mask].copy()
        LOGGER.info(
            "%d cameras remain after name filter (removed %d by token)",
            len(filtered),
            len(gdf) - len(filtered),
        )
        gdf = filtered

    gdf = gdf.sort_values("latitude").reset_index(drop=True)
    return gdf


def export_manifest(
    camera_gdf: gpd.GeoDataFrame,
    output_yaml: Path,
    output_json: Path,
) -> None:
    manifest = {
        "project": {
            "name": "Pax Corridor (Lexington–9th, 34th–66th)",
            "description": "Cameras filtered using DCM-derived corridor polygon",
        },
        "cameras": [],
    }

    for _, row in camera_gdf.iterrows():
        manifest["cameras"].append(
            {
                "id": row["id"],
                "name": row["name"],
                "area": row.get("area", ""),
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
                "source": row.get("source", ""),
            }
        )

    output_yaml.parent.mkdir(parents=True, exist_ok=True)
    output_yaml.write_text(yaml.safe_dump(manifest, sort_keys=False))
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(manifest["cameras"], indent=2))

    LOGGER.info("Saved YAML manifest to %s", output_yaml)
    LOGGER.info("Saved JSON camera list to %s", output_json)


def export_corridor_polygon(polygon: Polygon, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    gpd.GeoDataFrame({"id": [1]}, geometry=[polygon], crs="EPSG:4326").to_file(
        path, driver="GeoJSON"
    )
    LOGGER.info("Wrote corridor polygon to %s", path)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(level=args.log_level.upper(), format="%(levelname)s: %(message)s")

    cameras = load_cameras(args.cameras)
    polygon = build_corridor_polygon(args.dcm, args.street_buffer_m)
    filtered = filter_cameras_by_polygon(cameras, polygon)

    LOGGER.info("Final camera count: %d", len(filtered))

    export_manifest(filtered, args.output, args.output_json)
    if args.export_corridor:
        export_corridor_polygon(polygon, args.export_corridor)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
