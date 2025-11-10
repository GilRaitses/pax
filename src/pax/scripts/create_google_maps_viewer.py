#!/usr/bin/env python3
"""Create interactive Google Maps viewer with Voronoi zones and neighborhoods."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import geopandas as gpd
import yaml

LOGGER = logging.getLogger(__name__)

NEIGHBORHOOD_COLORS = {
    "Times Square": "#FF6B6B",
    "Garment District": "#4ECDC4",
    "Diamond District": "#FFE66D",
    "Murray Hill": "#95E1D3",
    "Rockefeller Center": "#F38181",
    "Billionaires' Row": "#AA96DA",
    "Midtown East": "#FCBAD3",
    "Lenox Hill": "#A8E6CF",
    "Grand Central": "#FD79A8",
    "Restaurant Row": "#FDCB6E",
    "Theater District": "#6C5CE7",
    "Fifth Avenue BID / Midtown": "#00B894",
    "Columbus Circle / Lincoln Square": "#74B9FF",
    "Midtown West": "#A29BFE",
    "Central Park South": "#55EFC4",
    "Koreatown": "#FFEAA7",
    "NoMad": "#DFE6E9",
    "Bryant Park": "#81ECEC",
    "Corporate Row / Avenue of Americas": "#B2BEC3",
    "Hell's Kitchen": "#FD79A8",
    "Chelsea / Penn Station Area": "#FDCB6E"
}

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <title>Pax Corridor - Google Maps with Voronoi Zones</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        html, body {{
            height: 100%;
            margin: 0;
            padding: 0;
            font-family: 'Roboto', 'Helvetica Neue', Arial, sans-serif;
        }}
        #map {{
            height: 100%;
        }}
        #legend {{
            background: white;
            padding: 15px;
            margin: 10px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
            max-height: 80vh;
            overflow-y: auto;
            font-size: 13px;
        }}
        #legend h3 {{
            margin: 0 0 10px 0;
            font-size: 16px;
            font-weight: 600;
        }}
        .legend-item {{
            margin: 6px 0;
            display: flex;
            align-items: center;
            cursor: pointer;
        }}
        .legend-item:hover {{
            background: #f5f5f5;
            padding: 2px;
            margin: 4px -2px;
            border-radius: 4px;
        }}
        .legend-color {{
            width: 18px;
            height: 18px;
            margin-right: 8px;
            border-radius: 50%;
            border: 2px solid #333;
        }}
        .info-window {{
            max-width: 300px;
        }}
        .info-window h4 {{
            margin: 0 0 8px 0;
            color: #333;
        }}
        .info-window p {{
            margin: 4px 0;
            font-size: 13px;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        let map;
        let markers = [];
        let zones = [];
        
        const cameras = {cameras_json};
        const voronoiZones = {voronoi_json};
        const neighborhoodColors = {colors_json};
        
        function initMap() {{
            map = new google.maps.Map(document.getElementById('map'), {{
                center: {{ lat: 40.758, lng: -73.980 }},
                zoom: 14,
                mapTypeId: 'roadmap',
                styles: [
                    {{
                        featureType: 'poi',
                        elementType: 'labels',
                        stylers: [{{ visibility: 'off' }}]
                    }}
                ]
            }});
            
            // Draw Voronoi zones if available
            if (voronoiZones && voronoiZones.features) {{
                voronoiZones.features.forEach((feature, idx) => {{
                    if (feature.geometry.type === 'Polygon') {{
                        const coords = feature.geometry.coordinates[0].map(coord => {{
                            return {{ lat: coord[1], lng: coord[0] }};
                        }});
                        
                        const neighborhood = feature.properties.neighborhood || 'Unknown';
                        const color = neighborhoodColors[neighborhood] || '#999999';
                        
                        const polygon = new google.maps.Polygon({{
                            paths: coords,
                            strokeColor: color,
                            strokeOpacity: 0.8,
                            strokeWeight: 2,
                            fillColor: color,
                            fillOpacity: 0.15,
                            map: map
                        }});
                        
                        zones.push({{ polygon, neighborhood }});
                        
                        // Add zone click handler
                        polygon.addListener('click', (event) => {{
                            const zoneInfo = new google.maps.InfoWindow({{
                                content: `<div class="info-window">
                                    <h4>${{neighborhood}}</h4>
                                    <p><strong>Zone:</strong> Voronoi tessellation</p>
                                    <p><strong>Camera:</strong> ${{feature.properties.name || 'N/A'}}</p>
                                </div>`,
                                position: event.latLng
                            }});
                            zoneInfo.open(map);
                        }});
                    }}
                }});
            }}
            
            // Add camera markers
            cameras.forEach(cam => {{
                const color = neighborhoodColors[cam.neighborhood] || '#999999';
                
                const marker = new google.maps.Marker({{
                    position: {{ lat: cam.latitude, lng: cam.longitude }},
                    map: map,
                    title: cam.name,
                    icon: {{
                        path: google.maps.SymbolPath.CIRCLE,
                        fillColor: color,
                        fillOpacity: 0.9,
                        strokeColor: '#333',
                        strokeWeight: 2,
                        scale: 8
                    }}
                }});
                
                const infoWindow = new google.maps.InfoWindow({{
                    content: `<div class="info-window">
                        <h4>${{cam.name}}</h4>
                        <p><strong>Neighborhood:</strong> ${{cam.neighborhood || 'Unknown'}}</p>
                        <p><strong>Coordinates:</strong><br>
                        Lat: ${{cam.latitude.toFixed(6)}}<br>
                        Lon: ${{cam.longitude.toFixed(6)}}</p>
                        <p><strong>Camera ID:</strong><br>
                        <small>${{cam.id}}</small></p>
                    </div>`
                }});
                
                marker.addListener('click', () => {{
                    infoWindow.open(map, marker);
                }});
                
                markers.push({{ marker, camera: cam }});
            }});
            
            // Add legend
            const legend = document.createElement('div');
            legend.id = 'legend';
            
            const neighborhoodCounts = {{}};
            cameras.forEach(cam => {{
                const n = cam.neighborhood || 'Unknown';
                neighborhoodCounts[n] = (neighborhoodCounts[n] || 0) + 1;
            }});
            
            const sorted = Object.keys(neighborhoodCounts).sort((a,b) => 
                neighborhoodCounts[b] - neighborhoodCounts[a]
            );
            
            legend.innerHTML = `<h3>Neighborhoods (${{cameras.length}} cameras)</h3>`;
            
            sorted.forEach(name => {{
                const color = neighborhoodColors[name] || '#999999';
                const count = neighborhoodCounts[name];
                
                const item = document.createElement('div');
                item.className = 'legend-item';
                item.innerHTML = `
                    <div class="legend-color" style="background-color: ${{color}}"></div>
                    <span>${{name}} (${{count}})</span>
                `;
                
                // Click to zoom to neighborhood
                item.addEventListener('click', () => {{
                    const neighborhoodCameras = cameras.filter(c => c.neighborhood === name);
                    if (neighborhoodCameras.length > 0) {{
                        const bounds = new google.maps.LatLngBounds();
                        neighborhoodCameras.forEach(c => {{
                            bounds.extend({{ lat: c.latitude, lng: c.longitude }});
                        }});
                        map.fitBounds(bounds);
                    }}
                }});
                
                legend.appendChild(item);
            }});
            
            map.controls[google.maps.ControlPosition.RIGHT_TOP].push(legend);
        }}
        
        window.initMap = initMap;
    </script>
    <script async defer
        src="https://maps.googleapis.com/maps/api/js?key={api_key}&callback=initMap">
    </script>
</body>
</html>
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cameras",
        type=Path,
        default=Path("data/cameras_with_neighborhoods.yaml"),
        help="Camera manifest with neighborhoods",
    )
    parser.add_argument(
        "--zones",
        type=Path,
        default=Path("data/voronoi_zones.geojson"),
        help="Voronoi zones GeoJSON (optional)",
    )
    parser.add_argument(
        "--api-key",
        default="AIzaSyD0tZfpi0PQPBbYh6iwMrkQKda9n1XPQnI",
        help="Google Maps API key",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/camera_map.html"),
        help="Output HTML file",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(level=args.log_level.upper(), format="%(levelname)s: %(message)s")

    with open(args.cameras) as f:
        data = yaml.safe_load(f)
    cameras = data["cameras"]

    LOGGER.info("Loaded %d cameras", len(cameras))

    # Load Voronoi zones if available
    voronoi_data = {}
    if args.zones.exists():
        voronoi_gdf = gpd.read_file(args.zones)
        voronoi_data = json.loads(voronoi_gdf.to_json())
        LOGGER.info("Loaded %d Voronoi zones", len(voronoi_gdf))
    else:
        LOGGER.warning("Voronoi zones not found at %s", args.zones)

    html = HTML_TEMPLATE.format(
        cameras_json=json.dumps(cameras),
        voronoi_json=json.dumps(voronoi_data),
        colors_json=json.dumps(NEIGHBORHOOD_COLORS),
        api_key=args.api_key,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html)
    LOGGER.info("Saved Google Maps viewer to %s", args.output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

