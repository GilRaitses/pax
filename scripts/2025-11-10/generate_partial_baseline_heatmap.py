#!/usr/bin/env python3
"""Generate partial baseline heatmap using stress scores.

Wrapper around generate_baseline_heatmap.py that adapts stress scores format.
"""

import argparse
import json
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

from generate_baseline_heatmap import main as heatmap_main


def convert_stress_scores_format(stress_scores_path: Path) -> dict[str, float]:
    """Convert stress scores format to camera_id -> stress_score mapping."""
    with open(stress_scores_path) as f:
        data = json.load(f)

    # Extract camera-level stress scores
    camera_stress = data.get("camera_stress", {})
    
    # Convert to simple dict: camera_id -> stress_score
    stress_scores = {}
    for camera_id, camera_data in camera_stress.items():
        stress_scores[camera_id] = camera_data.get("mean_stress", 0.0)
    
    return stress_scores


def generate_partial_heatmap(
    stress_scores_path: Path,
    output_path: Path | None = None,
    zones_path: Path | None = None,
    cameras_path: Path | None = None,
    corridor_path: Path | None = None,
) -> None:
    """Generate partial baseline heatmap."""
    # Convert stress scores format
    stress_scores = convert_stress_scores_format(stress_scores_path)
    
    # Create temporary JSON file with converted format
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(stress_scores, f, indent=2)
        temp_stress_path = Path(f.name)
    
    try:
        # Build arguments for heatmap script
        argv = [
            "--stress-scores", str(temp_stress_path),
            "--output", str(output_path) if output_path else "docs/figures/baseline_heatmap_partial.png",
        ]
        
        if zones_path:
            argv.extend(["--zones", str(zones_path)])
        if cameras_path:
            argv.extend(["--cameras", str(cameras_path)])
        if corridor_path:
            argv.extend(["--corridor", str(corridor_path)])
        
        # Run heatmap script
        heatmap_main(argv)
    finally:
        # Clean up temp file
        if temp_stress_path.exists():
            temp_stress_path.unlink()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate partial baseline heatmap")
    parser.add_argument(
        "--stress-scores",
        type=Path,
        default=Path("data/stress_scores_preliminary.json"),
        help="Path to stress scores JSON (default: data/stress_scores_preliminary.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/figures/baseline_heatmap_partial.png"),
        help="Output path for heatmap (default: docs/figures/baseline_heatmap_partial.png)",
    )
    parser.add_argument(
        "--zones",
        type=Path,
        default=Path("data/geojson/voronoi_zones.geojson"),
        help="Path to Voronoi zones GeoJSON",
    )
    parser.add_argument(
        "--cameras",
        type=Path,
        default=Path("data/geojson/corridor_cameras.geojson"),
        help="Path to cameras GeoJSON",
    )
    parser.add_argument(
        "--corridor",
        type=Path,
        default=Path("data/geojson/corridor_polygon.geojson"),
        help="Path to corridor polygon GeoJSON",
    )

    args = parser.parse_args()

    if not args.stress_scores.exists():
        print(f"ERROR: Stress scores file not found: {args.stress_scores}")
        print("Run compute_stress_scores.py first to generate stress scores.")
        sys.exit(1)

    generate_partial_heatmap(
        args.stress_scores,
        args.output,
        args.zones,
        args.cameras,
        args.corridor,
    )


if __name__ == "__main__":
    main()

