"""Extract REAL intersection points where streets actually cross."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely.geometry import Point

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dcm-shapefile",
        type=Path,
        required=True,
        help="DCM StreetCenterLine shapefile path",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/voronoi_zones/real_intersections.json"),
        help="Output JSON file",
    )
    parser.add_argument(
        "--bounds",
        nargs=4,
        type=float,
        metavar=("LAT_MIN", "LAT_MAX", "LON_MIN", "LON_MAX"),
        default=(40.744, 40.773, -74.003, -73.967),
        help="Corridor bounds",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.00005,
        help="Tolerance for rounding coordinates (default: 0.00005 ~ 5m)",
    )
    parser.add_argument(
        "--min-streets",
        type=int,
        default=2,
        help="Minimum number of streets that must meet at an intersection (default: 2)",
    )
    return parser


def extract_real_intersections(
    dcm_path: Path,
    bounds: tuple[float, float, float, float],
    tolerance: float = 0.00001,
) -> np.ndarray:
    """Extract intersection points where streets actually cross.
    
    Returns array of [lon, lat] coordinates.
    """
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
    
    # Filter to corridor bounds
    lat_min, lat_max, lon_min, lon_max = bounds
    corridor_streets = manhattan.cx[lon_min:lon_max, lat_min:lat_max]
    
    LOGGER.info("Found %d street segments in corridor", len(corridor_streets))
    
    # Find intersections where streets cross
    LOGGER.info("Computing real intersection points (where streets cross)...")
    intersection_coords = set()
    intersection_points = []
    
    checked_pairs = set()
    total_pairs = len(corridor_streets) * (len(corridor_streets) - 1) // 2
    
    for i, (idx1, row1) in enumerate(corridor_streets.iterrows()):
        geom1 = row1.geometry
        
        for j, (idx2, row2) in enumerate(corridor_streets.iterrows()):
            if i >= j:  # Avoid duplicate pairs
                continue
            
            pair_key = (min(idx1, idx2), max(idx1, idx2))
            if pair_key in checked_pairs:
                continue
            checked_pairs.add(pair_key)
            
            geom2 = row2.geometry
            
            try:
                if geom1.intersects(geom2):
                    intersection = geom1.intersection(geom2)
                    
                    if intersection.geom_type == "Point":
                        lon, lat = intersection.x, intersection.y
                        
                        # Filter to bounds
                        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
                            # Round to tolerance to deduplicate nearby points
                            coord = (round(lon / tolerance) * tolerance,
                                    round(lat / tolerance) * tolerance)
                            
                            if coord not in intersection_coords:
                                intersection_coords.add(coord)
                                intersection_points.append([lon, lat])
                    
                    elif intersection.geom_type == "MultiPoint":
                        for point in intersection.geoms:
                            lon, lat = point.x, point.y
                            if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
                                coord = (round(lon / tolerance) * tolerance,
                                        round(lat / tolerance) * tolerance)
                                if coord not in intersection_coords:
                                    intersection_coords.add(coord)
                                    intersection_points.append([lon, lat])
            
            except Exception as e:
                LOGGER.debug("Error checking intersection: %s", e)
                continue
        
        if (i + 1) % 50 == 0:
            LOGGER.info("  Processed %d/%d streets, found %d intersections...",
                       i + 1, len(corridor_streets), len(intersection_points))
    
    intersections = np.array(intersection_points)
    LOGGER.info("Found %d real intersections", len(intersections))
    
    return intersections


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    
    intersections = extract_real_intersections(
        args.dcm_shapefile,
        args.bounds,
        args.tolerance,
    )
    
    # Save to JSON
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(intersections.tolist(), f, indent=2)
    
    LOGGER.info("Saved %d intersections to %s", len(intersections), args.output)
    
    print(f"\n{'=' * 70}")
    print("REAL INTERSECTIONS EXTRACTED")
    print(f"{'=' * 70}")
    print(f"Total intersections: {len(intersections)}")
    print(f"Output: {args.output}")
    print(f"\nThese are actual street crossings, not arbitrary points!")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

