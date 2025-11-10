"""Calculate weighted stress scores for intersections using Voronoi zone boundaries.

Each intersection inherits stress scores from:
- Its own zone's camera (weight: 1.0)
- Neighboring zones' cameras (weight: 0.5 for adjacent, 0.25 for second-order neighbors)

This enables Pareto front optimization for pathfinding with spatial influence.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
from shapely.geometry import Point

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--zones",
        type=Path,
        default=Path("data/geojson/voronoi_zones.geojson"),
        help="Voronoi zones GeoJSON file",
    )
    parser.add_argument(
        "--zones-json",
        type=Path,
        default=Path("data/voronoi_zones/voronoi_zones.json"),
        help="Voronoi zones JSON file with coordinate arrays",
    )
    parser.add_argument(
        "--intersections",
        type=Path,
        help="Intersections file (CSV with lat/lon or GeoJSON)",
    )
    parser.add_argument(
        "--camera-stress",
        type=Path,
        help="Camera stress scores file (JSON dict: camera_id -> stress_score)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/voronoi_zones/weighted_stress_scores.json"),
        help="Output file for weighted stress scores",
    )
    parser.add_argument(
        "--neighbor-weight",
        type=float,
        default=0.5,
        help="Weight for adjacent zone neighbors (default: 0.5)",
    )
    parser.add_argument(
        "--second-order-weight",
        type=float,
        default=0.25,
        help="Weight for second-order neighbors (default: 0.25)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level",
    )
    return parser


def load_zones(zones_path: Path, zones_json_path: Path) -> tuple[gpd.GeoDataFrame, dict[str, Any]]:
    """Load Voronoi zones from GeoJSON and JSON coordinate arrays."""
    zones_gdf = gpd.read_file(zones_path)
    
    with open(zones_json_path) as f:
        zones_data = json.load(f)
    
    LOGGER.info("Loaded %d Voronoi zones", len(zones_gdf))
    return zones_gdf, zones_data


def find_neighbors(zones_gdf: gpd.GeoDataFrame) -> dict[int, list[int]]:
    """Find neighboring zones (zones that share edges or vertices).
    
    Returns:
        Dictionary mapping zone index -> list of neighbor zone indices
    """
    neighbors = {}
    
    for idx, zone in zones_gdf.iterrows():
        zone_geom = zone.geometry
        zone_idx = zone['index']
        
        # Find zones that touch this zone
        touching = zones_gdf[zones_gdf.geometry.touches(zone_geom)]
        neighbor_indices = [int(row['index']) for _, row in touching.iterrows()]
        neighbors[zone_idx] = neighbor_indices
    
    LOGGER.info("Computed neighbor relationships for %d zones", len(neighbors))
    return neighbors


def find_second_order_neighbors(
    neighbors: dict[int, list[int]],
    zone_idx: int,
) -> list[int]:
    """Find second-order neighbors (neighbors of neighbors, excluding direct neighbors)."""
    direct_neighbors = set(neighbors.get(zone_idx, []))
    second_order = set()
    
    for neighbor_idx in direct_neighbors:
        neighbor_neighbors = neighbors.get(neighbor_idx, [])
        second_order.update(neighbor_neighbors)
    
    # Remove self and direct neighbors
    second_order.discard(zone_idx)
    second_order -= direct_neighbors
    
    return list(second_order)


def calculate_weighted_stress(
    point: Point,
    zones_gdf: gpd.GeoDataFrame,
    neighbors: dict[int, list[int]],
    camera_stress: dict[str, float],
    neighbor_weight: float = 0.5,
    second_order_weight: float = 0.25,
) -> dict[str, Any]:
    """Calculate weighted stress score for an intersection point.
    
    Args:
        point: Shapely Point (lon, lat order)
        zones_gdf: GeoDataFrame of Voronoi zones
        neighbors: Dictionary of zone neighbors
        camera_stress: Dictionary mapping camera_id -> stress_score
        neighbor_weight: Weight for adjacent neighbors
        second_order_weight: Weight for second-order neighbors
    
    Returns:
        Dictionary with stress score and zone information
    """
    # Find containing zone
    containing = zones_gdf[zones_gdf.geometry.contains(point)]
    
    if len(containing) == 0:
        # Find nearest zone
        distances = zones_gdf.geometry.distance(point)
        nearest_idx = distances.idxmin()
        containing = zones_gdf.loc[[nearest_idx]]
    
    zone = containing.iloc[0]
    zone_idx = int(zone['index'])
    camera_id = zone['camera_id']
    
    # Base stress from own zone
    base_stress = camera_stress.get(camera_id, 0.0)
    
    # Stress from adjacent neighbors
    neighbor_indices = neighbors.get(zone_idx, [])
    neighbor_stress = 0.0
    neighbor_contributions = []
    
    for n_idx in neighbor_indices:
        neighbor_zone = zones_gdf[zones_gdf['index'] == n_idx].iloc[0]
        n_camera_id = neighbor_zone['camera_id']
        n_stress = camera_stress.get(n_camera_id, 0.0)
        weighted_n_stress = n_stress * neighbor_weight
        neighbor_stress += weighted_n_stress
        neighbor_contributions.append({
            "zone_index": n_idx,
            "camera_id": n_camera_id,
            "stress": n_stress,
            "weighted_stress": weighted_n_stress,
        })
    
    # Stress from second-order neighbors
    second_order_indices = find_second_order_neighbors(neighbors, zone_idx)
    second_order_stress = 0.0
    second_order_contributions = []
    
    for so_idx in second_order_indices:
        so_zone = zones_gdf[zones_gdf['index'] == so_idx].iloc[0]
        so_camera_id = so_zone['camera_id']
        so_stress = camera_stress.get(so_camera_id, 0.0)
        weighted_so_stress = so_stress * second_order_weight
        second_order_stress += weighted_so_stress
        second_order_contributions.append({
            "zone_index": so_idx,
            "camera_id": so_camera_id,
            "stress": so_stress,
            "weighted_stress": weighted_so_stress,
        })
    
    # Total weighted stress
    total_stress = base_stress + neighbor_stress + second_order_stress
    
    return {
        "point": {"lon": point.x, "lat": point.y},
        "zone_index": zone_idx,
        "camera_id": camera_id,
        "camera_name": zone['camera_name'],
        "base_stress": base_stress,
        "neighbor_stress": neighbor_stress,
        "second_order_stress": second_order_stress,
        "total_weighted_stress": total_stress,
        "contributions": {
            "own_zone": {
                "camera_id": camera_id,
                "stress": base_stress,
                "weight": 1.0,
            },
            "neighbors": neighbor_contributions,
            "second_order": second_order_contributions,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    
    logging.basicConfig(level=args.log_level.upper(), format="%(levelname)s: %(message)s")
    
    # Load zones
    zones_gdf, zones_data = load_zones(args.zones, args.zones_json)
    
    # Find neighbors
    neighbors = find_neighbors(zones_gdf)
    
    # Load camera stress scores (if provided)
    camera_stress = {}
    if args.camera_stress and args.camera_stress.exists():
        with open(args.camera_stress) as f:
            camera_stress = json.load(f)
        LOGGER.info("Loaded stress scores for %d cameras", len(camera_stress))
    else:
        # Default: all zeros (example)
        camera_stress = {zone['camera_id']: 0.0 for zone in zones_data['zones']}
        LOGGER.warning("No camera stress file provided, using zeros")
    
    # Process intersections if provided
    if args.intersections:
        # TODO: Load intersections from file
        LOGGER.info("Intersection processing not yet implemented")
        return 0
    
    # Example: Calculate stress for zone centers
    results = []
    for idx, zone in zones_gdf.iterrows():
        center_point = Point(zone.geometry.centroid.x, zone.geometry.centroid.y)
        result = calculate_weighted_stress(
            center_point,
            zones_gdf,
            neighbors,
            camera_stress,
            args.neighbor_weight,
            args.second_order_weight,
        )
        results.append(result)
    
    # Save results
    output_data = {
        "metadata": {
            "total_zones": len(zones_gdf),
            "neighbor_weight": args.neighbor_weight,
            "second_order_weight": args.second_order_weight,
        },
        "zone_stress_scores": results,
    }
    
    with open(args.output, "w") as f:
        json.dump(output_data, f, indent=2)
    
    LOGGER.info("Saved weighted stress scores to %s", args.output)
    
    print("\n" + "=" * 70)
    print("WEIGHTED STRESS SCORING COMPLETE")
    print("=" * 70)
    print(f"\nProcessed {len(results)} zones")
    print(f"Neighbor weight: {args.neighbor_weight}")
    print(f"Second-order weight: {args.second_order_weight}")
    print(f"\nSample results:")
    for result in results[:3]:
        print(f"\n  Zone {result['zone_index']}: {result['camera_name']}")
        print(f"    Base stress: {result['base_stress']:.3f}")
        print(f"    Neighbor stress: {result['neighbor_stress']:.3f}")
        print(f"    Second-order stress: {result['second_order_stress']:.3f}")
        print(f"    Total weighted: {result['total_weighted_stress']:.3f}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())


