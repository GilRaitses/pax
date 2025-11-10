#!/usr/bin/env python3
"""Organize data files into subdirectories while preserving critical files.

This script organizes non-critical files into logical subdirectories:
- data/manifests/ - Camera manifests and related JSON/YAML
- data/geojson/ - GeoJSON files (polygons, zones, cameras)
- data/voronoi/ - Voronoi zone data (already exists)

Critical files remain in root data/:
- corridor_cameras_numbered.json/yaml
- intersections.json
"""

from __future__ import annotations

import argparse
import logging
import shutil
from pathlib import Path
from datetime import datetime

LOGGER = logging.getLogger(__name__)

# Critical files that MUST stay in root
CRITICAL_FILES = {
    "corridor_cameras_numbered.json",
    "corridor_cameras_numbered.yaml",
    "intersections.json",
}

# File organization rules
ORGANIZATION_RULES = {
    "manifests": {
        "patterns": [
            "corridor_cameras.json",
            "corridor_cameras.yaml",
            "corridor_88_cameras.json",
            "corridor_108_cameras.json",
            "corridor_108_cameras.yaml",
            "corridor_clean_cameras.json",
            "cameras_with_neighborhoods.json",
            "cameras_with_neighborhoods.yaml",
            "camera_ids.json",
            "nyc_cameras_full.json",
            "neighborhood_stats.json",
            "image_manifest.yaml",
        ],
        "description": "Camera manifests and related JSON/YAML files",
    },
    "geojson": {
        "patterns": [
            "corridor_polygon.geojson",
            "corridor_cameras.geojson",
            "voronoi_zones.geojson",
        ],
        "description": "GeoJSON files (polygons, zones, cameras)",
    },
    "polygons": {
        "patterns": [
            "constrained_boundary_polygon.json",
        ],
        "description": "Boundary polygon definitions",
    },
}


def organize_files(data_dir: Path, dry_run: bool = False) -> dict:
    """Organize files into subdirectories.
    
    Returns statistics dict.
    """
    stats = {
        "files_moved": 0,
        "dirs_created": 0,
        "skipped": 0,
        "errors": 0,
    }
    
    # Create subdirectories
    subdirs = {}
    for subdir_name in ORGANIZATION_RULES.keys():
        subdir_path = data_dir / subdir_name
        if not dry_run:
            subdir_path.mkdir(exist_ok=True)
            if not (subdir_path / ".gitkeep").exists():
                (subdir_path / ".gitkeep").touch()
        subdirs[subdir_name] = subdir_path
        stats["dirs_created"] += 1
        LOGGER.info("Created/verified directory: %s", subdir_path)
    
    # Organize files
    for item in data_dir.iterdir():
        if item.is_dir() or item.name.startswith("."):
            continue
        
        # Skip critical files
        if item.name in CRITICAL_FILES:
            LOGGER.debug("Skipping critical file: %s", item.name)
            stats["skipped"] += 1
            continue
        
        # Find matching subdirectory
        moved = False
        for subdir_name, rules in ORGANIZATION_RULES.items():
            if item.name in rules["patterns"]:
                dest = subdirs[subdir_name] / item.name
                
                try:
                    if dry_run:
                        LOGGER.info("[DRY RUN] Would move: %s -> %s", item.name, dest)
                    else:
                        shutil.move(str(item), str(dest))
                        LOGGER.info("Moved: %s -> %s", item.name, dest)
                    
                    stats["files_moved"] += 1
                    moved = True
                    break
                except Exception as e:
                    LOGGER.error("Error moving %s: %s", item.name, e)
                    stats["errors"] += 1
        
        if not moved:
            LOGGER.debug("No rule for file: %s (will remain in root)", item.name)
    
    return stats


def update_script_references(data_dir: Path, dry_run: bool = False) -> list[str]:
    """Find scripts that reference old paths and need updating.
    
    Returns list of files that need path updates.
    """
    # This is informational - actual updates would require manual review
    scripts_to_check = []
    
    for subdir_name, rules in ORGANIZATION_RULES.items():
        for pattern in rules["patterns"]:
            # Check if any scripts reference this file
            # (This is a placeholder - actual implementation would grep codebase)
            scripts_to_check.append(f"Files referencing data/{pattern} may need updates")
    
    return scripts_to_check


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Organize data files into subdirectories"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Data directory (default: data)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be organized without actually moving files",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (default: INFO)",
    )
    
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(levelname)s: %(message)s",
    )
    
    data_dir = args.data_dir.resolve()
    
    if not data_dir.exists():
        LOGGER.error("Data directory does not exist: %s", data_dir)
        return 1
    
    LOGGER.info("=" * 60)
    LOGGER.info("Data File Organization")
    LOGGER.info("=" * 60)
    LOGGER.info("Source: %s", data_dir)
    LOGGER.info("Mode: %s", "DRY RUN" if args.dry_run else "LIVE")
    LOGGER.info("")
    
    LOGGER.info("Critical files that will remain in root:")
    for critical_file in CRITICAL_FILES:
        critical_path = data_dir / critical_file
        if critical_path.exists():
            LOGGER.info("  ✓ %s", critical_file)
        else:
            LOGGER.warning("  ✗ %s (not found!)", critical_file)
    LOGGER.info("")
    
    LOGGER.info("Organization structure:")
    for subdir_name, rules in ORGANIZATION_RULES.items():
        LOGGER.info("  %s/ - %s", subdir_name, rules["description"])
        LOGGER.info("    Patterns: %s", ", ".join(rules["patterns"][:3]) + "...")
    LOGGER.info("")
    
    if args.dry_run:
        LOGGER.info("Scanning files...")
    
    stats = organize_files(data_dir, dry_run=args.dry_run)
    
    if args.dry_run:
        LOGGER.info("")
        LOGGER.info("DRY RUN: No files were actually moved.")
        LOGGER.info("Run without --dry-run to perform the organization.")
        return 0
    
    # Summary
    LOGGER.info("")
    LOGGER.info("=" * 60)
    LOGGER.info("Organization Complete")
    LOGGER.info("=" * 60)
    LOGGER.info("Files moved: %d", stats["files_moved"])
    LOGGER.info("Directories created: %d", stats["dirs_created"])
    LOGGER.info("Skipped (critical): %d", stats["skipped"])
    LOGGER.info("Errors: %d", stats["errors"])
    LOGGER.info("")
    LOGGER.info("NOTE: Scripts referencing moved files may need path updates.")
    LOGGER.info("Check script defaults for: data/corridor_cameras.*, data/voronoi_zones.geojson, etc.")
    
    return 0 if stats["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

