"""Generate Voronoi tessellation zones for camera locations and export to shapefile.

Each Voronoi cell represents the influence zone of a camera. The boundaries can be used
for weighted stress score calculations where intersections inherit scores from neighboring
zones (Pareto front optimization).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from scipy.spatial import Voronoi
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
import geopandas as gpd

from ..config import PaxSettings

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("cameras.yaml"),
        help="Camera manifest YAML file (default: cameras.yaml)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/voronoi_zones"),
        help="Output directory for shapefiles and metadata (default: data/voronoi_zones)",
    )
    parser.add_argument(
        "--bounds",
        nargs=4,
        type=float,
        metavar=("LAT_MIN", "LAT_MAX", "LON_MIN", "LON_MAX"),
        default=None,
        help="Bounding box for clipping Voronoi cells (default: auto-calculate from cameras)",
    )
    parser.add_argument(
        "--buffer",
        type=float,
        default=0.01,
        help="Buffer distance in degrees for bounding box (default: 0.01)",
    )
    parser.add_argument(
        "--dcm-shapefile",
        type=Path,
        help="DCM StreetCenterLine shapefile path (for clipping to street network)",
    )
    parser.add_argument(
        "--clip-to-streets",
        action="store_true",
        help="Clip Voronoi cells to street network boundaries",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level",
    )
    return parser


def load_cameras(manifest_path: Path) -> list[dict[str, Any]]:
    """Load camera locations from manifest."""
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)
    
    cameras = manifest.get("cameras", [])
    LOGGER.info("Loaded %d cameras from %s", len(cameras), manifest_path)
    return cameras


def compute_voronoi(
    cameras: list[dict[str, Any]],
    bounds: tuple[float, float, float, float] | None = None,
    buffer: float = 0.01,
) -> tuple[Voronoi, np.ndarray, list[dict[str, Any]]]:
    """Compute Voronoi tessellation for camera locations.
    
    Note: Voronoi uses (lat, lon) for input but scipy.spatial.Voronoi
    works in Euclidean space, so we use (lon, lat) to match standard
    coordinate ordering (x, y) = (lon, lat).
    
    Returns:
        voronoi: scipy.spatial.Voronoi object
        points: numpy array of [lon, lat] points (for Voronoi computation)
        camera_metadata: list of camera dicts with metadata
    """
    # Extract camera locations - use (lon, lat) for Voronoi (matches term project)
    points = []
    camera_metadata = []
    
    for cam in cameras:
        lat = cam.get("latitude")
        lon = cam.get("longitude")
        if lat is None or lon is None:
            LOGGER.warning("Skipping camera %s: missing coordinates", cam.get("id"))
            continue
        
        # Store as (lon, lat) for Voronoi computation (matches term project style)
        points.append([lon, lat])
        camera_metadata.append(cam)
    
    if not points:
        raise ValueError("No valid camera coordinates found")
    
    points = np.array(points)
    
    # Calculate bounds if not provided (lon_min, lon_max, lat_min, lat_max)
    if bounds is None:
        lon_min, lon_max = points[:, 0].min(), points[:, 0].max()
        lat_min, lat_max = points[:, 1].min(), points[:, 1].max()
        bounds = (
            lat_min - buffer,
            lat_max + buffer,
            lon_min - buffer,
            lon_max + buffer,
        )
    
    LOGGER.info("Computing Voronoi for %d points", len(points))
    LOGGER.info("Bounds: lat [%.4f, %.4f], lon [%.4f, %.4f]", *bounds)
    
    # Compute Voronoi diagram (using lon/lat as x/y)
    voronoi = Voronoi(points)
    
    return voronoi, points, camera_metadata


def voronoi_cell_to_polygon(
    voronoi: Voronoi,
    region_index: int,
    bounds: tuple[float, float, float, float],
) -> Polygon | None:
    """Convert a Voronoi region to a Shapely Polygon.
    
    Clips infinite regions to the bounding box.
    Note: Voronoi vertices are in (lon, lat) since we passed (lon, lat) to Voronoi.
    Shapely also uses (lon, lat), so no conversion needed.
    """
    region = voronoi.regions[voronoi.point_region[region_index]]
    
    if not region or -1 in region:
        # Infinite region - need to clip to bounds
        vertices = []
        for v_idx in region:
            if v_idx == -1:
                continue
            # Voronoi vertices are already (lon, lat)
            lon, lat = voronoi.vertices[v_idx]
            vertices.append((lon, lat))
        
        if len(vertices) < 3:
            return None
        
        # Create polygon and clip to bounds
        try:
            poly = Polygon(vertices)
            lat_min, lat_max, lon_min, lon_max = bounds
            
            # Create bounding box polygon (lon, lat order for Shapely)
            bbox = Polygon([
                (lon_min, lat_min),
                (lon_max, lat_min),
                (lon_max, lat_max),
                (lon_min, lat_max),
            ])
            
            # Clip to bounds
            clipped = poly.intersection(bbox)
            if clipped.is_empty:
                return None
            
            # Handle MultiPolygon case
            if hasattr(clipped, 'geoms'):
                # Take the largest polygon
                clipped = max(clipped.geoms, key=lambda p: p.area)
            
            return clipped if isinstance(clipped, Polygon) else None
        except Exception as e:
            LOGGER.warning("Failed to create polygon for region %d: %s", region_index, e)
            return None
    else:
        # Finite region - vertices are already (lon, lat)
        vertices = [tuple(voronoi.vertices[v_idx]) for v_idx in region]
        if len(vertices) < 3:
            return None
        try:
            return Polygon(vertices)
        except Exception as e:
            LOGGER.warning("Failed to create polygon for region %d: %s", region_index, e)
            return None


def clip_to_street_network(
    gdf: gpd.GeoDataFrame,
    dcm_path: Path,
    bounds: tuple[float, float, float, float],
) -> gpd.GeoDataFrame:
    """Clip Voronoi zones to street network boundaries from DCM shapefile.
    
    This ensures zones respect actual street boundaries rather than extending
    into buildings/parks/etc. Uses a tighter buffer for cleaner boundaries.
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
    
    # Create buffer around streets (to represent walkable area)
    # Reproject to metric CRS for accurate buffering
    LOGGER.info("Reprojecting to metric CRS for accurate buffering...")
    corridor_streets_metric = corridor_streets.to_crs(epsg=3857)  # Web Mercator (meters)
    
    # Buffer in meters (tighter for cleaner boundaries)
    street_buffer_m = 20  # 20 meters buffer around streets
    LOGGER.info("Buffering streets with %dm...", street_buffer_m)
    
    street_polygons = corridor_streets_metric.buffer(street_buffer_m)
    
    # Convert back to geographic CRS
    from geopandas import GeoSeries
    street_polygons = GeoSeries(street_polygons, crs="EPSG:3857").to_crs("EPSG:4326")
    
    # Union all street buffers to create walkable area
    LOGGER.info("Creating street network buffer (this may take a moment)...")
    walkable_area = unary_union(street_polygons.tolist())
    
    # Clip Voronoi zones to walkable area
    LOGGER.info("Clipping Voronoi zones to street network...")
    clipped_geometries = []
    for idx, zone in gdf.iterrows():
        clipped = zone.geometry.intersection(walkable_area)
        
        if clipped.is_empty:
            LOGGER.warning("Zone %d completely outside street network, keeping original", zone['index'])
            clipped_geometries.append(zone.geometry)
            continue
        
        # Handle MultiPolygon - take largest connected component
        if hasattr(clipped, 'geoms'):
            # Sort by area and take largest
            polygons = [p for p in clipped.geoms if isinstance(p, Polygon)]
            if polygons:
                clipped = max(polygons, key=lambda p: p.area)
            else:
                clipped_geometries.append(zone.geometry)
                continue
        
        if isinstance(clipped, Polygon):
            # Simplify polygon to reduce jagged edges
            clipped = clipped.simplify(tolerance=0.00001, preserve_topology=True)
            clipped_geometries.append(clipped)
        else:
            # Fallback to original if clipping produced non-polygon
            LOGGER.warning("Zone %d clipping produced non-polygon, keeping original", zone['index'])
            clipped_geometries.append(zone.geometry)
    
    gdf_clipped = gdf.copy()
    gdf_clipped = gdf_clipped.set_geometry(clipped_geometries)
    
    # Update coordinate arrays after clipping
    LOGGER.info("Updating coordinate arrays after clipping...")
    for idx, zone in gdf_clipped.iterrows():
        polygon = zone.geometry
        coords_lonlat = np.array(polygon.exterior.coords)
        coords_latlon = np.column_stack([coords_lonlat[:, 1], coords_lonlat[:, 0]])
        
        gdf_clipped.at[idx, "coordinates"] = coords_latlon.tolist()
        gdf_clipped.at[idx, "coordinates_lonlat"] = coords_lonlat.tolist()
        gdf_clipped.at[idx, "num_vertices"] = len(coords_latlon)
        gdf_clipped.at[idx, "zone_area_m2"] = polygon.area * 111320 * 111320 * np.cos(np.radians(zone["latitude"]))
    
    LOGGER.info("Clipped %d zones to street network", len(gdf_clipped))
    return gdf_clipped


def create_voronoi_zones(
    voronoi: Voronoi,
    points: np.ndarray,
    camera_metadata: list[dict[str, Any]],
    bounds: tuple[float, float, float, float],
    clip_to_streets: bool = False,
    dcm_path: Path | None = None,
) -> gpd.GeoDataFrame:
    """Create GeoDataFrame with Voronoi zones and metadata."""
    
    geometries = []
    features = []
    
    for i, (point, camera) in enumerate(zip(points, camera_metadata)):
        polygon = voronoi_cell_to_polygon(voronoi, i, bounds)
        
        # If polygon is None or empty (infinite region), create a bounding box zone
        if polygon is None or polygon.is_empty:
            LOGGER.warning("Camera %s has infinite region, creating bounded zone", camera.get("name"))
            # Create a square zone around the camera point as fallback
            lat_min, lat_max, lon_min, lon_max = bounds
            camera_lon, camera_lat = point[0], point[1]
            
            # Create a reasonable sized zone around the camera (about 0.002 degrees = ~200m)
            zone_size = 0.002
            fallback_bounds = Polygon([
                (camera_lon - zone_size, camera_lat - zone_size),
                (camera_lon + zone_size, camera_lat - zone_size),
                (camera_lon + zone_size, camera_lat + zone_size),
                (camera_lon - zone_size, camera_lat + zone_size),
            ])
            
            # Clip to overall bounds
            bbox = Polygon([
                (lon_min, lat_min),
                (lon_max, lat_min),
                (lon_max, lat_max),
                (lon_min, lat_max),
            ])
            polygon = fallback_bounds.intersection(bbox)
            
            # Handle MultiPolygon
            if hasattr(polygon, 'geoms'):
                polygon = max(polygon.geoms, key=lambda p: p.area)
            
            if polygon.is_empty or not isinstance(polygon, Polygon):
                LOGGER.error("Failed to create fallback zone for camera %s", camera.get("name"))
                # Use a tiny circle as last resort
                from shapely.geometry import Point as ShapelyPoint
                point_geom = ShapelyPoint(camera_lon, camera_lat)
                polygon = point_geom.buffer(0.0005)  # ~50m radius
        
        geometries.append(polygon)
        
        # Extract coordinates as array (polygon is in lon/lat from Shapely)
        coords_lonlat = np.array(polygon.exterior.coords)  # Shapely uses (lon, lat)
        coords_latlon = np.column_stack([coords_lonlat[:, 1], coords_lonlat[:, 0]])  # Convert to (lat, lon)
        
        # Note: point is (lon, lat) from Voronoi computation
        camera_lon, camera_lat = point[0], point[1]
        
        features.append({
            "index": i,
            "camera_id": camera.get("id"),
            "camera_name": camera.get("name"),
            "latitude": float(camera_lat),
            "longitude": float(camera_lon),
            "area": camera.get("area", ""),
            "priority": camera.get("priority", "medium"),
            "avenue": camera.get("name", "").split("@")[0].strip() if "@" in camera.get("name", "") else "",
            "zone_area_m2": polygon.area * 111320 * 111320 * np.cos(np.radians(camera_lat)),  # Approximate area in m²
            "coordinates": coords_latlon.tolist(),  # Full coordinate array [lat, lon] pairs
            "coordinates_lonlat": coords_lonlat.tolist(),  # Also store [lon, lat] for Shapely compatibility
            "num_vertices": len(coords_latlon),
        })
    
    gdf = gpd.GeoDataFrame(features, geometry=geometries, crs="EPSG:4326")
    
    LOGGER.info("Created %d Voronoi zones", len(gdf))
    
    # Clip to street network if requested
    if clip_to_streets and dcm_path and dcm_path.exists():
        gdf = clip_to_street_network(gdf, dcm_path, bounds)
    
    return gdf


def export_zones(
    gdf: gpd.GeoDataFrame,
    output_dir: Path,
) -> dict[str, Path]:
    """Export Voronoi zones to multiple formats."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    outputs = {}
    
    # 1. Shapefile (for GIS software)
    shapefile_path = output_dir / "voronoi_zones.shp"
    gdf.to_file(shapefile_path, driver="ESRI Shapefile")
    outputs["shapefile"] = shapefile_path
    LOGGER.info("Exported shapefile: %s", shapefile_path)
    
    # 2. GeoJSON (for web mapping and Python)
    geojson_path = output_dir / "voronoi_zones.geojson"
    gdf.to_file(geojson_path, driver="GeoJSON")
    outputs["geojson"] = geojson_path
    LOGGER.info("Exported GeoJSON: %s", geojson_path)
    
    # 3. JSON with coordinate arrays and indices (for Python processing)
    json_data = {
        "metadata": {
            "total_zones": len(gdf),
            "crs": str(gdf.crs),
            "bounds": {
                "lat_min": float(gdf.bounds.miny.min()),
                "lat_max": float(gdf.bounds.maxy.max()),
                "lon_min": float(gdf.bounds.minx.min()),
                "lon_max": float(gdf.bounds.maxx.max()),
            },
        },
        "zones": [],
    }
    
    for idx, row in gdf.iterrows():
        zone_data = {
            "index": int(row["index"]),
            "camera_id": row["camera_id"],
            "camera_name": row["camera_name"],
            "latitude": float(row["latitude"]),
            "longitude": float(row["longitude"]),
            "coordinates": row.get("coordinates", []),  # Array of [lat, lon] pairs
            "coordinates_lonlat": row.get("coordinates_lonlat", []),  # Array of [lon, lat] pairs for Shapely
            "num_vertices": int(row.get("num_vertices", 0)),
            "area_m2": float(row.get("zone_area_m2", 0.0)),
            "properties": {
                "area": row.get("area", ""),
                "priority": row.get("priority", "medium"),
                "avenue": row.get("avenue", ""),
            },
        }
        json_data["zones"].append(zone_data)
    
    json_path = output_dir / "voronoi_zones.json"
    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=2)
    outputs["json"] = json_path
    LOGGER.info("Exported JSON: %s", json_path)
    
    # 4. NumPy arrays for fast computation
    # Extract coordinate arrays indexed by zone
    npz_path = output_dir / "voronoi_zones.npz"
    np_arrays = {}
    for idx, row in gdf.iterrows():
        zone_idx = int(row["index"])
        np_arrays[f"zone_{zone_idx}_coords"] = np.array(row["coordinates"])
        np_arrays[f"zone_{zone_idx}_center"] = np.array([row["latitude"], row["longitude"]])
    
    # Also save indices mapping
    indices = np.array([int(row["index"]) for _, row in gdf.iterrows()])
    camera_ids = np.array([row["camera_id"] for _, row in gdf.iterrows()])
    centers = np.array([[row["latitude"], row["longitude"]] for _, row in gdf.iterrows()])
    
    np.savez(
        npz_path,
        indices=indices,
        camera_ids=camera_ids,
        centers=centers,
        **np_arrays,
    )
    outputs["npz"] = npz_path
    LOGGER.info("Exported NumPy arrays: %s", npz_path)
    
    # 5. Summary metadata
    summary_path = output_dir / "voronoi_summary.yaml"
    summary = {
        "total_zones": len(gdf),
        "bounds": json_data["metadata"]["bounds"],
        "crs": str(gdf.crs),
        "files": {
            "shapefile": str(shapefile_path.relative_to(output_dir)),
            "geojson": str(geojson_path.relative_to(output_dir)),
            "json": str(json_path.relative_to(output_dir)),
            "npz": str(npz_path.relative_to(output_dir)),
        },
        "zones_by_avenue": {},
    }
    
    # Count zones by avenue
    for _, row in gdf.iterrows():
        avenue = row["avenue"] or "Unknown"
        summary["zones_by_avenue"][avenue] = summary["zones_by_avenue"].get(avenue, 0) + 1
    
    with open(summary_path, "w") as f:
        yaml.dump(summary, f, default_flow_style=False, sort_keys=False)
    outputs["summary"] = summary_path
    LOGGER.info("Exported summary: %s", summary_path)
    
    return outputs


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    
    logging.basicConfig(level=args.log_level.upper(), format="%(levelname)s: %(message)s")
    
    # Load cameras
    cameras = load_cameras(args.manifest)
    
    # Compute Voronoi
    voronoi, points, camera_metadata = compute_voronoi(
        cameras,
        bounds=args.bounds,
        buffer=args.buffer,
    )
    
    # Create bounds tuple (lat_min, lat_max, lon_min, lon_max)
    if args.bounds:
        bounds = (args.bounds[0], args.bounds[1], args.bounds[2], args.bounds[3])
    else:
        # points[:, 0] stores longitudes, points[:, 1] stores latitudes
        lon_min, lon_max = points[:, 0].min() - args.buffer, points[:, 0].max() + args.buffer
        lat_min, lat_max = points[:, 1].min() - args.buffer, points[:, 1].max() + args.buffer
        bounds = (lat_min, lat_max, lon_min, lon_max)
    
    # Create Voronoi zones GeoDataFrame
    gdf = create_voronoi_zones(
        voronoi, 
        points, 
        camera_metadata, 
        bounds,
        clip_to_streets=args.clip_to_streets,
        dcm_path=args.dcm_shapefile,
    )
    
    # Export to multiple formats
    outputs = export_zones(gdf, args.output_dir)
    
    print("\n" + "=" * 70)
    print("VORONOI ZONES GENERATED")
    print("=" * 70)
    print(f"\nTotal zones: {len(gdf)}")
    print(f"\nOutput files:")
    for format_name, path in outputs.items():
        print(f"  {format_name:12s}: {path}")
    
    print(f"\n{'=' * 70}")
    print("USAGE FOR WEIGHTED STRESS SCORING")
    print("=" * 70)
    print("""
Each Voronoi zone can be used for:
1. Geometric isolation: Check if intersection point is within zone boundary
2. Neighbor detection: Find adjacent zones (share edges/vertices)
3. Weighted scoring: Intersection inherits stress from:
   - Its own zone's camera score (weight: 1.0)
   - Neighboring zones' scores (weight: 0.5 for adjacent, 0.25 for second-order)

Example Python usage:
    import geopandas as gpd
    import json
    
    # Load zones
    zones = gpd.read_file('data/voronoi_zones/voronoi_zones.geojson')
    
    # Load coordinate arrays with indices
    with open('data/voronoi_zones/voronoi_zones.json') as f:
        zones_data = json.load(f)
    
    # For each intersection point:
    point = Point(lon, lat)  # Note: Shapely uses (lon, lat)
    containing_zone = zones[zones.contains(point)]
    
    # Find neighbors (zones that touch)
    neighbors = zones[zones.touches(containing_zone.geometry.iloc[0])]
    
    # Calculate weighted stress score
    base_stress = camera_stress[containing_zone['camera_id']]
    neighbor_stress = sum(camera_stress[n['camera_id']] * 0.5 for n in neighbors)
    weighted_stress = base_stress + neighbor_stress
    """)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

