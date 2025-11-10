"""Generate collection progress dashboard HTML.

Shows progress toward 2-week goal (672 images/camera), displays images per camera,
and shows collection rate trends.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

LOGGER = logging.getLogger(__name__)

GOAL_IMAGES_PER_CAMERA = 672  # 2 weeks * 48 images/day (every 30 min)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/manifests/image_manifest.yaml"),
        help="Path to image manifest YAML",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/progress_dashboard.html"),
        help="Output path for dashboard HTML (default: docs/progress_dashboard.html)",
    )
    parser.add_argument(
        "--goal",
        type=int,
        default=GOAL_IMAGES_PER_CAMERA,
        help=f"Goal images per camera (default: {GOAL_IMAGES_PER_CAMERA})",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level",
    )
    return parser


def load_manifest(manifest_path: Path) -> dict[str, Any]:
    """Load manifest YAML."""
    with open(manifest_path) as f:
        return yaml.safe_load(f)


def calculate_progress_stats(
    manifest: dict[str, Any], goal_per_camera: int
) -> dict[str, Any]:
    """Calculate progress statistics."""
    cameras_data = manifest.get("cameras", {})
    metadata = manifest.get("metadata", {})

    camera_progress = []
    total_images = 0
    total_cameras = len(cameras_data)
    cameras_with_images = 0

    # Calculate collection rate over time
    daily_counts = defaultdict(int)
    for camera_id, camera_data in cameras_data.items():
        image_count = camera_data.get("total_images", 0)
        total_images += image_count
        if image_count > 0:
            cameras_with_images += 1

        progress_pct = (image_count / goal_per_camera * 100) if goal_per_camera > 0 else 0
        camera_progress.append(
            {
                "camera_id": camera_id,
                "images": image_count,
                "goal": goal_per_camera,
                "progress": min(progress_pct, 100),
                "remaining": max(goal_per_camera - image_count, 0),
            }
        )

        # Track daily collection
        images_by_date = camera_data.get("images_by_date", {})
        for date_str, count in images_by_date.items():
            daily_counts[date_str] += count

    # Calculate collection rate trends
    sorted_dates = sorted(daily_counts.keys())
    collection_rate = []
    for date_str in sorted_dates:
        collection_rate.append({"date": date_str, "count": daily_counts[date_str]})

    # Calculate overall progress
    total_goal = total_cameras * goal_per_camera
    overall_progress = (total_images / total_goal * 100) if total_goal > 0 else 0

    # Estimate completion date
    if collection_rate and len(collection_rate) >= 2:
        recent_days = collection_rate[-7:]  # Last 7 days
        avg_daily = sum(d["count"] for d in recent_days) / len(recent_days) if recent_days else 0
        remaining_images = total_goal - total_images
        days_to_complete = remaining_images / avg_daily if avg_daily > 0 else None
        if days_to_complete:
            estimated_completion = datetime.now() + timedelta(days=int(days_to_complete))
        else:
            estimated_completion = None
    else:
        estimated_completion = None

    return {
        "total_images": total_images,
        "total_cameras": total_cameras,
        "cameras_with_images": cameras_with_images,
        "goal_per_camera": goal_per_camera,
        "total_goal": total_goal,
        "overall_progress": overall_progress,
        "camera_progress": sorted(camera_progress, key=lambda x: x["images"], reverse=True),
        "collection_rate": collection_rate,
        "estimated_completion": estimated_completion.isoformat() if estimated_completion else None,
        "collection_start": metadata.get("collection_period", {}).get("start_date"),
        "collection_end": metadata.get("collection_period", {}).get("end_date"),
    }


def generate_dashboard_html(stats: dict[str, Any], output_path: Path) -> None:
    """Generate HTML dashboard."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    camera_progress_json = json.dumps(stats["camera_progress"])
    collection_rate_json = json.dumps(stats["collection_rate"])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Collection Progress Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            padding: 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            padding: 30px;
        }}
        
        h1 {{
            color: #667eea;
            margin-bottom: 10px;
            font-size: 2.5em;
        }}
        
        .subtitle {{
            color: #666;
            margin-bottom: 30px;
            font-size: 1.1em;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        
        .stat-label {{
            font-size: 0.9em;
            opacity: 0.9;
            margin-bottom: 10px;
        }}
        
        .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        
        .stat-subtext {{
            font-size: 0.85em;
            opacity: 0.8;
        }}
        
        .progress-section {{
            margin-bottom: 40px;
        }}
        
        .progress-bar-container {{
            background: #f0f0f0;
            border-radius: 10px;
            height: 40px;
            margin: 20px 0;
            position: relative;
            overflow: hidden;
        }}
        
        .progress-bar {{
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            height: 100%;
            border-radius: 10px;
            transition: width 0.5s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 1.1em;
        }}
        
        .chart-container {{
            margin: 30px 0;
            padding: 20px;
            background: #f9f9f9;
            border-radius: 10px;
        }}
        
        .camera-list {{
            max-height: 600px;
            overflow-y: auto;
            border: 1px solid #ddd;
            border-radius: 10px;
            padding: 15px;
        }}
        
        .camera-item {{
            padding: 15px;
            margin-bottom: 10px;
            background: white;
            border-radius: 8px;
            border-left: 4px solid #667eea;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }}
        
        .camera-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        
        .camera-id {{
            font-weight: bold;
            color: #333;
            font-size: 0.9em;
        }}
        
        .camera-count {{
            color: #667eea;
            font-weight: bold;
            font-size: 1.1em;
        }}
        
        .camera-progress-bar {{
            background: #e0e0e0;
            border-radius: 5px;
            height: 20px;
            margin-top: 8px;
            overflow: hidden;
        }}
        
        .camera-progress-fill {{
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            height: 100%;
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            padding-right: 8px;
            color: white;
            font-size: 0.75em;
            font-weight: bold;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        
        th {{
            background: #667eea;
            color: white;
            font-weight: bold;
        }}
        
        tr:hover {{
            background: #f5f5f5;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Collection Progress Dashboard</h1>
        <p class="subtitle">Tracking progress toward 2-week collection goal (672 images/camera)</p>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Images Collected</div>
                <div class="stat-value">{stats['total_images']:,}</div>
                <div class="stat-subtext">of {stats['total_goal']:,} goal</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-label">Overall Progress</div>
                <div class="stat-value">{stats['overall_progress']:.1f}%</div>
                <div class="stat-subtext">Collection complete</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-label">Active Cameras</div>
                <div class="stat-value">{stats['cameras_with_images']}</div>
                <div class="stat-subtext">of {stats['total_cameras']} total</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-label">Goal per Camera</div>
                <div class="stat-value">{stats['goal_per_camera']}</div>
                <div class="stat-subtext">images (2 weeks)</div>
            </div>
        </div>
        
        <div class="progress-section">
            <h2>Overall Collection Progress</h2>
            <div class="progress-bar-container">
                <div class="progress-bar" style="width: {min(stats['overall_progress'], 100)}%">
                    {stats['overall_progress']:.1f}%
                </div>
            </div>
            <p style="margin-top: 10px; color: #666;">
                {stats['total_images']:,} / {stats['total_goal']:,} images collected
                {f" | Estimated completion: {datetime.fromisoformat(stats['estimated_completion']).strftime('%Y-%m-%d')}" if stats['estimated_completion'] else ""}
            </p>
        </div>
        
        <div class="chart-container">
            <h2>Collection Rate Trend</h2>
            <canvas id="collectionRateChart"></canvas>
        </div>
        
        <div class="chart-container">
            <h2>Images per Camera</h2>
            <canvas id="cameraProgressChart"></canvas>
        </div>
        
        <div class="progress-section">
            <h2>Camera-Level Progress</h2>
            <div class="camera-list" id="cameraList"></div>
        </div>
    </div>
    
    <script>
        const cameraProgress = {camera_progress_json};
        const collectionRate = {collection_rate_json};
        
        // Collection Rate Chart
        const rateCtx = document.getElementById('collectionRateChart').getContext('2d');
        new Chart(rateCtx, {{
            type: 'line',
            data: {{
                labels: collectionRate.map(d => d.date),
                datasets: [{{
                    label: 'Images Collected',
                    data: collectionRate.map(d => d.count),
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.4,
                    fill: true
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{
                        display: true,
                        position: 'top'
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: 'Images'
                        }}
                    }},
                    x: {{
                        title: {{
                            display: true,
                            text: 'Date'
                        }}
                    }}
                }}
            }}
        }});
        
        // Camera Progress Chart (top 20)
        const topCameras = cameraProgress.slice(0, 20);
        const progressCtx = document.getElementById('cameraProgressChart').getContext('2d');
        new Chart(progressCtx, {{
            type: 'bar',
            data: {{
                labels: topCameras.map(c => c.camera_id.substring(0, 20) + '...'),
                datasets: [{{
                    label: 'Images Collected',
                    data: topCameras.map(c => c.images),
                    backgroundColor: '#667eea',
                    borderColor: '#764ba2',
                    borderWidth: 1
                }}, {{
                    label: 'Goal',
                    data: topCameras.map(c => c.goal),
                    backgroundColor: 'rgba(102, 126, 234, 0.2)',
                    borderColor: '#764ba2',
                    borderWidth: 1,
                    type: 'line'
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{
                        display: true,
                        position: 'top'
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: 'Images'
                        }}
                    }}
                }}
            }}
        }});
        
        // Camera List
        const cameraList = document.getElementById('cameraList');
        cameraProgress.forEach(camera => {{
            const item = document.createElement('div');
            item.className = 'camera-item';
            item.innerHTML = `
                <div class="camera-header">
                    <span class="camera-id">${{camera.camera_id}}</span>
                    <span class="camera-count">${{camera.images}} / ${{camera.goal}}</span>
                </div>
                <div class="camera-progress-bar">
                    <div class="camera-progress-fill" style="width: ${{Math.min(camera.progress, 100)}}%">
                        ${{camera.progress.toFixed(1)}}%
                    </div>
                </div>
            `;
            cameraList.appendChild(item);
        }});
    </script>
</body>
</html>
"""

    with open(output_path, "w") as f:
        f.write(html)

    LOGGER.info("Progress dashboard written to %s", output_path)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=args.log_level.upper(), format="%(levelname)s: %(message)s"
    )

    if not args.manifest.exists():
        LOGGER.error("Manifest not found: %s", args.manifest)
        return 1

    LOGGER.info("Loading manifest from %s", args.manifest)
    manifest = load_manifest(args.manifest)

    LOGGER.info("Calculating progress statistics...")
    stats = calculate_progress_stats(manifest, args.goal)

    LOGGER.info("Generating dashboard HTML...")
    generate_dashboard_html(stats, args.output)

    LOGGER.info("Dashboard generation complete:")
    LOGGER.info("  Total images: %d", stats["total_images"])
    LOGGER.info("  Overall progress: %.1f%%", stats["overall_progress"])
    LOGGER.info("  Cameras with images: %d / %d", stats["cameras_with_images"], stats["total_cameras"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

