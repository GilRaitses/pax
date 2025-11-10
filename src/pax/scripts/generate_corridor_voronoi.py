"""Generate Voronoi zones for the Lexington–9th Ave camera corridor."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import coloredlogs
import geopandas as gpd
import pandas as pd
import yaml
from dataclasses import asdict

from ..corridor import derive_corridor_bounds
from ..voronoi import generate_corridor_voronoi

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/manifests/lex_to_9_corridor.yaml"),
        help="Filtered camera manifest",
    )
    parser.add_argument(
        "--dcm-shapefile",
        type=Path,
        default=Path("docs/data/dcm/DCM_StreetCenterLine.shp"),
        help="Street centerline shapefile",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/voronoi/corridor"),
        help="Directory for Voronoi outputs",
    )
    parser.add_argument(
        "--street-buffer-m",
        type=float,
        default=18.0,
        help="Street buffer in meters when clipping to walkable area",
    )
    parser.add_argument(
        "--south-street",
        type=int,
        default=34,
        help="Corridor south street number",
    )
    parser.add_argument(
        "--north-street",
        type=int,
        default=66,
        help="Corridor north street number",
    )
    parser.add_argument(
        "--east-avenue",
        type=str,
        default="Lexington Avenue",
        help="Corridor east boundary avenue name",
    )
    parser.add_argument(
        "--west-avenue",
        type=str,
        default="9 Avenue",
        help="Corridor west boundary avenue name",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level",
    )
    return parser


def load_manifest(path: Path) -> gpd.GeoDataFrame:
    with open(path) as fh:
        data = yaml.safe_load(fh)
    cameras = pd.DataFrame(data.get("cameras", []))
    if cameras.empty:
        raise ValueError(f"Manifest {path} contains no cameras")
    geometry = gpd.points_from_xy(cameras["longitude"], cameras["latitude"], crs="EPSG:4326")
    gdf = gpd.GeoDataFrame(cameras, geometry=geometry)
    LOGGER.info("Loaded %d cameras from manifest", len(gdf))
    return gdf


def export_outputs(result, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    geojson_path = output_dir / "voronoi_zones.geojson"
    shapefile_path = output_dir / "voronoi_zones.shp"
    json_path = output_dir / "voronoi_zones.json"

    result.zones.to_file(geojson_path, driver="GeoJSON")
    LOGGER.info("Saved GeoJSON zones to %s", geojson_path)

    result.zones.to_file(shapefile_path)
    LOGGER.info("Saved shapefile to %s", shapefile_path)

    records = result.zones.drop(columns="geometry").to_dict(orient="records")
    with open(json_path, "w") as fh:
        json.dump({"zones": records, "bounds": asdict(result.bounds)}, fh, indent=2)
    LOGGER.info("Saved JSON summary to %s", json_path)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    coloredlogs.install(level=args.log_level.upper(), fmt="%(levelname)s %(message)s")

    cameras = load_manifest(args.manifest)

    bounds = derive_corridor_bounds(
        args.dcm_shapefile,
        south_street=args.south_street,
        north_street=args.north_street,
        east_avenue=args.east_avenue,
        west_avenue=args.west_avenue,
    )

    result = generate_corridor_voronoi(
        cameras,
        bounds,
        dcm_path=args.dcm_shapefile,
        street_buffer_m=args.street_buffer_m,
    )

    export_outputs(result, args.output_dir)

    print("\n" + "=" * 70)
    print("CORRIDOR VORONOI ZONES CREATED")
    print("=" * 70)
    print(f"Total zones: {len(result.zones)}")
    print(f"GeoJSON: {args.output_dir / 'voronoi_zones.geojson'}")
    print(f"Shapefile: {args.output_dir / 'voronoi_zones.shp'}")
    print(f"JSON summary: {args.output_dir / 'voronoi_zones.json'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
