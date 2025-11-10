"""Create interactive HTML visualization for selecting cameras from Voronoi zones."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import geopandas as gpd
import yaml

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--zones",
        type=Path,
        default=Path("data/voronoi_zones/expanded_34th_66th/voronoi_zones.geojson"),
        help="Voronoi zones GeoJSON file",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("cameras_expanded_34th_66th.yaml"),
        help="Camera manifest YAML file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/voronoi_zones/camera_selector.html"),
        help="Output HTML file",
    )
    return parser


def create_selector_html(
    zones: gpd.GeoDataFrame,
    manifest: dict,
    output_path: Path,
) -> None:
    """Create interactive HTML for camera selection."""
    
    # Convert zones to GeoJSON for Leaflet
    zones_geojson = json.loads(zones.to_json())
    
    # Prepare camera data
    cameras_data = []
    for cam in manifest.get("cameras", []):
        cameras_data.append({
            "id": cam["id"],
            "name": cam["name"],
            "latitude": cam["latitude"],
            "longitude": cam["longitude"],
            "selected": True,  # Default: all selected
        })
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Camera Selector - Voronoi Zones</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            display: flex;
            height: 100vh;
            overflow: hidden;
        }}
        
        #map {{
            flex: 1;
            height: 100vh;
        }}
        
        #sidebar {{
            width: 400px;
            background: #f8f9fa;
            border-left: 1px solid #dee2e6;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
        }}
        
        #sidebar-header {{
            padding: 20px;
            background: white;
            border-bottom: 2px solid #667eea;
        }}
        
        #sidebar-header h1 {{
            font-size: 20px;
            color: #333;
            margin-bottom: 10px;
        }}
        
        #stats {{
            display: flex;
            gap: 15px;
            margin-top: 10px;
        }}
        
        .stat {{
            flex: 1;
            padding: 8px;
            background: #f0f0f0;
            border-radius: 4px;
            text-align: center;
        }}
        
        .stat-label {{
            font-size: 11px;
            color: #666;
            text-transform: uppercase;
        }}
        
        .stat-value {{
            font-size: 18px;
            font-weight: bold;
            color: #667eea;
            margin-top: 4px;
        }}
        
        #camera-list {{
            flex: 1;
            overflow-y: auto;
            padding: 10px;
        }}
        
        .camera-item {{
            background: white;
            border: 2px solid #dee2e6;
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 10px;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        
        .camera-item:hover {{
            border-color: #667eea;
            box-shadow: 0 2px 8px rgba(102, 126, 234, 0.2);
        }}
        
        .camera-item.selected {{
            border-color: #667eea;
            background: #f0f4ff;
        }}
        
        .camera-item.deselected {{
            opacity: 0.5;
            background: #f8f9fa;
        }}
        
        .camera-checkbox {{
            width: 20px;
            height: 20px;
            border: 2px solid #667eea;
            border-radius: 4px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }}
        
        .camera-checkbox.checked {{
            background: #667eea;
        }}
        
        .camera-checkbox.checked::after {{
            content: '✓';
            color: white;
            font-size: 14px;
            font-weight: bold;
        }}
        
        .camera-info {{
            flex: 1;
        }}
        
        .camera-name {{
            font-weight: 600;
            color: #333;
            margin-bottom: 4px;
        }}
        
        .camera-id {{
            font-size: 11px;
            color: #999;
            font-family: monospace;
        }}
        
        #actions {{
            padding: 20px;
            background: white;
            border-top: 1px solid #dee2e6;
        }}
        
        .btn {{
            width: 100%;
            padding: 12px;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            margin-bottom: 10px;
        }}
        
        .btn-primary {{
            background: #667eea;
            color: white;
        }}
        
        .btn-primary:hover {{
            background: #5568d3;
        }}
        
        .btn-secondary {{
            background: #e9ecef;
            color: #333;
        }}
        
        .btn-secondary:hover {{
            background: #dee2e6;
        }}
        
        .voronoi-zone {{
            fill: rgba(102, 126, 234, 0.1);
            stroke: rgba(102, 126, 234, 0.3);
            stroke-width: 2;
            cursor: pointer;
            transition: all 0.2s;
        }}
        
        .voronoi-zone:hover {{
            fill: rgba(102, 126, 234, 0.2);
            stroke: rgba(102, 126, 234, 0.5);
        }}
        
        .voronoi-zone.deselected {{
            fill: rgba(200, 200, 200, 0.1);
            stroke: rgba(200, 200, 200, 0.3);
            opacity: 0.3;
        }}
        
        .camera-marker {{
            cursor: pointer;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    <div id="sidebar">
        <div id="sidebar-header">
            <h1>Camera Selector</h1>
            <div id="stats">
                <div class="stat">
                    <div class="stat-label">Total</div>
                    <div class="stat-value" id="total-count">{len(cameras_data)}</div>
                </div>
                <div class="stat">
                    <div class="stat-label">Selected</div>
                    <div class="stat-value" id="selected-count">{len(cameras_data)}</div>
                </div>
            </div>
        </div>
        <div id="camera-list"></div>
        <div id="actions">
            <button class="btn btn-secondary" onclick="selectAll()">Select All</button>
            <button class="btn btn-secondary" onclick="deselectAll()">Deselect All</button>
            <button class="btn btn-primary" onclick="exportSelected()">Export Selected</button>
        </div>
    </div>

    <script>
        // Camera data
        const cameras = {json.dumps(cameras_data)};
        const zonesGeoJSON = {json.dumps(zones_geojson)};
        
        // Initialize map
        const map = L.map('map').setView([40.760, -73.980], 14);
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }}).addTo(map);
        
        // Store selected cameras
        let selectedCameras = new Set(cameras.map(c => c.id));
        
        // Create camera markers and zones
        const cameraMarkers = {{}};
        const zoneLayers = {{}};
        
        // Add Voronoi zones
        zonesGeoJSON.features.forEach((feature, idx) => {{
            const cameraId = feature.properties.camera_id;
            const zoneLayer = L.geoJSON(feature, {{
                style: {{
                    fillColor: '#667eea',
                    fillOpacity: 0.1,
                    color: '#667eea',
                    weight: 2,
                    opacity: 0.3
                }},
                onEachFeature: function(feature, layer) {{
                    layer.on({{
                        click: function() {{
                            toggleCamera(cameraId);
                        }}
                    }});
                }}
            }}).addTo(map);
            
            zoneLayers[cameraId] = zoneLayer;
            updateZoneStyle(cameraId);
        }});
        
        // Add camera markers
        cameras.forEach(camera => {{
            const marker = L.marker([camera.latitude, camera.longitude], {{
                icon: L.divIcon({{
                    className: 'camera-marker',
                    html: `<div style="background: #27ae60; width: 20px; height: 20px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>`,
                    iconSize: [20, 20],
                    iconAnchor: [10, 10]
                }})
            }}).addTo(map);
            
            marker.on('click', function() {{
                toggleCamera(camera.id);
            }});
            
            marker.bindPopup(`<b>${{camera.name}}</b><br><small>${{camera.id}}</small>`);
            cameraMarkers[camera.id] = marker;
        }});
        
        // Render camera list
        function renderCameraList() {{
            const list = document.getElementById('camera-list');
            list.innerHTML = '';
            
            cameras.forEach(camera => {{
                const isSelected = selectedCameras.has(camera.id);
                const item = document.createElement('div');
                item.className = `camera-item ${{isSelected ? 'selected' : 'deselected'}}`;
                item.onclick = () => toggleCamera(camera.id);
                
                item.innerHTML = `
                    <div class="camera-checkbox ${{isSelected ? 'checked' : ''}}"></div>
                    <div class="camera-info">
                        <div class="camera-name">${{camera.name}}</div>
                        <div class="camera-id">${{camera.id.substring(0, 8)}}...</div>
                    </div>
                `;
                
                list.appendChild(item);
            }});
            
            updateStats();
        }}
        
        function toggleCamera(cameraId) {{
            if (selectedCameras.has(cameraId)) {{
                selectedCameras.delete(cameraId);
            }} else {{
                selectedCameras.add(cameraId);
            }}
            
            updateZoneStyle(cameraId);
            renderCameraList();
        }}
        
        function updateZoneStyle(cameraId) {{
            const isSelected = selectedCameras.has(cameraId);
            const zoneLayer = zoneLayers[cameraId];
            
            if (zoneLayer) {{
                zoneLayer.setStyle({{
                    fillOpacity: isSelected ? 0.1 : 0.05,
                    opacity: isSelected ? 0.3 : 0.1,
                    fillColor: isSelected ? '#667eea' : '#999999',
                    color: isSelected ? '#667eea' : '#999999'
                }});
            }}
            
            const marker = cameraMarkers[cameraId];
            if (marker) {{
                marker.setOpacity(isSelected ? 1.0 : 0.3);
            }}
        }}
        
        function selectAll() {{
            cameras.forEach(c => selectedCameras.add(c.id));
            cameras.forEach(c => updateZoneStyle(c.id));
            renderCameraList();
        }}
        
        function deselectAll() {{
            selectedCameras.clear();
            cameras.forEach(c => updateZoneStyle(c.id));
            renderCameraList();
        }}
        
        function updateStats() {{
            document.getElementById('selected-count').textContent = selectedCameras.size;
        }}
        
        function exportSelected() {{
            const selected = cameras.filter(c => selectedCameras.has(c.id));
            
            const manifest = {{
                project: {{
                    name: "Pax NYC - Selected Cameras",
                    description: `Selected ${{selected.length}} cameras from expanded corridor`,
                    study_area: {{
                        start: "Selected area",
                        goal: "Selected area",
                        bounds: "Selected cameras"
                    }}
                }},
                schedule: {{
                    interval_minutes: 30,
                    active_hours: {{
                        start: "06:00",
                        end: "22:00"
                    }},
                    timezone: "America/New_York"
                }},
                cameras: selected.map(c => ({{
                    id: c.id,
                    name: c.name,
                    area: "Manhattan",
                    latitude: c.latitude,
                    longitude: c.longitude,
                    priority: "medium"
                }}))
            }};
            
            const blob = new Blob([JSON.stringify(manifest, null, 2)], {{ type: 'application/json' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'cameras_selected.json';
            a.click();
            URL.revokeObjectURL(url);
            
            // Also create YAML version
            const yamlContent = `project:
  name: "Pax NYC - Selected Cameras"
  description: "Selected ${{selected.length}} cameras from expanded corridor"
  study_area:
    start: "Selected area"
    goal: "Selected area"
    bounds: "Selected cameras"
schedule:
  interval_minutes: 30
  active_hours:
    start: "06:00"
    end: "22:00"
  timezone: "America/New_York"
cameras:
${{selected.map(c => `- id: ${{c.id}}
  name: "${{c.name}}"
  area: Manhattan
  latitude: ${{c.latitude}}
  longitude: ${{c.longitude}}
  priority: medium`).join('\\n')}}
`;
            
            const yamlBlob = new Blob([yamlContent], {{ type: 'text/yaml' }});
            const yamlUrl = URL.createObjectURL(yamlBlob);
            const yamlA = document.createElement('a');
            yamlA.href = yamlUrl;
            yamlA.download = 'cameras_selected.yaml';
            yamlA.click();
            URL.revokeObjectURL(yamlUrl);
            
            alert(`Exported ${{selected.length}} selected cameras!\\n\\nFiles downloaded:\\n- cameras_selected.json\\n- cameras_selected.yaml`);
        }}
        
        // Initial render
        renderCameraList();
    </script>
</body>
</html>
"""
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(html_content)
    
    LOGGER.info("Created interactive selector at %s", output_path)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    
    # Load zones
    zones = gpd.read_file(args.zones)
    LOGGER.info("Loaded %d zones", len(zones))
    
    # Load manifest
    with open(args.manifest) as f:
        manifest = yaml.safe_load(f)
    LOGGER.info("Loaded %d cameras", len(manifest.get("cameras", [])))
    
    # Create HTML
    create_selector_html(zones, manifest, args.output)
    
    print("\n" + "=" * 70)
    print("INTERACTIVE CAMERA SELECTOR CREATED")
    print("=" * 70)
    print(f"\nOpen in browser: {args.output}")
    print("\nFeatures:")
    print("  • Click cameras or zones to select/deselect")
    print("  • Use sidebar to see all cameras")
    print("  • Export selected cameras as YAML/JSON")
    print("  • Visual feedback shows selected vs deselected cameras")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())


