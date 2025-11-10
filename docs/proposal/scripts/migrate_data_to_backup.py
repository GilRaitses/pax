#!/usr/bin/env python3
"""Safely migrate non-critical files from data/ to docs/data_bkup/.

This script preserves critical files that are actively used by the codebase
and moves everything else to docs/data_bkup/ for archival.
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
from pathlib import Path
from datetime import datetime

LOGGER = logging.getLogger(__name__)

# Critical files that MUST stay in root data/
CRITICAL_FILES = {
    "corridor_cameras_numbered.json",
    "corridor_cameras_numbered.yaml",
    "intersections.json",
}

# Directories that are already gitignored and safe to move
SAFE_TO_MOVE_DIRS = {
    "raw",
    "warehouse",
    "packages",
    "exports",
    "processed",
    "images_by_intersection",
    "voronoi",
    "manifests",
}


def find_files_to_move(data_dir: Path, backup_dir: Path) -> list[tuple[Path, Path]]:
    """Find files that can be safely moved.
    
    Returns list of (source, destination) tuples.
    """
    moves = []
    
    # Check all files and directories in data/
    for item in data_dir.iterdir():
        if item.name.startswith("."):
            continue  # Skip hidden files
        
        # Skip critical files
        if item.name in CRITICAL_FILES:
            LOGGER.debug("Skipping critical file: %s", item.name)
            continue
        
        # Handle directories
        if item.is_dir():
            if item.name in SAFE_TO_MOVE_DIRS:
                dest = backup_dir / item.name
                moves.append((item, dest))
            else:
                # Check if directory contains only safe-to-move files
                has_critical = False
                for subitem in item.rglob("*"):
                    if subitem.is_file() and subitem.name in CRITICAL_FILES:
                        has_critical = True
                        break
                
                if not has_critical:
                    dest = backup_dir / item.name
                    moves.append((item, dest))
        
        # Handle files
        elif item.is_file():
            dest = backup_dir / item.name
            
            # Check if destination already exists
            if dest.exists():
                # Compare file sizes and modification times
                src_stat = item.stat()
                dest_stat = dest.stat()
                
                if src_stat.st_mtime > dest_stat.st_mtime:
                    # Source is newer, will overwrite
                    LOGGER.info("Destination exists but source is newer: %s", item.name)
                    moves.append((item, dest))
                else:
                    # Destination is newer or same, skip
                    LOGGER.info("Skipping %s (destination is newer or same)", item.name)
                    continue
            else:
                moves.append((item, dest))
    
    return moves


def move_files(moves: list[tuple[Path, Path]], dry_run: bool = False) -> dict:
    """Move files and directories.
    
    Returns statistics dict.
    """
    stats = {
        "files_moved": 0,
        "dirs_moved": 0,
        "bytes_moved": 0,
        "skipped": 0,
        "errors": 0,
    }
    
    for src, dest in moves:
        try:
            if src.is_file():
                size = src.stat().st_size
                if dry_run:
                    LOGGER.info("[DRY RUN] Would move file: %s -> %s (%d bytes)", 
                              src, dest, size)
                else:
                    # Ensure destination directory exists
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(src), str(dest))
                    LOGGER.info("Moved file: %s -> %s (%d bytes)", src.name, dest, size)
                
                stats["files_moved"] += 1
                stats["bytes_moved"] += size
            
            elif src.is_dir():
                if dry_run:
                    # Count files in directory
                    file_count = sum(1 for _ in src.rglob("*") if _.is_file())
                    LOGGER.info("[DRY RUN] Would move directory: %s -> %s (%d files)", 
                              src, dest, file_count)
                else:
                    # Ensure parent directory exists
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    
                    # If destination exists, merge contents
                    if dest.exists():
                        LOGGER.warning("Destination directory exists, merging: %s", dest)
                        # Move contents instead of whole directory
                        for subitem in src.iterdir():
                            subdest = dest / subitem.name
                            if subitem.is_dir():
                                if subdest.exists():
                                    shutil.copytree(str(subitem), str(subdest), 
                                                  dirs_exist_ok=True)
                                    shutil.rmtree(str(subitem))
                                else:
                                    shutil.move(str(subitem), str(subdest))
                            else:
                                if subdest.exists():
                                    LOGGER.warning("Skipping duplicate file: %s", subitem.name)
                                    subitem.unlink()
                                else:
                                    shutil.move(str(subitem), str(subdest))
                        # Remove now-empty source directory
                        try:
                            src.rmdir()
                        except OSError:
                            pass  # Directory not empty, that's fine
                    else:
                        shutil.move(str(src), str(dest))
                    
                    LOGGER.info("Moved directory: %s -> %s", src.name, dest)
                
                stats["dirs_moved"] += 1
        
        except Exception as e:
            LOGGER.error("Error moving %s: %s", src, e)
            stats["errors"] += 1
    
    return stats


def create_migration_log(data_dir: Path, backup_dir: Path, moves: list[tuple[Path, Path]], 
                         stats: dict) -> Path:
    """Create a log file documenting the migration."""
    log_file = backup_dir / f"migration_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "source_dir": str(data_dir),
        "destination_dir": str(backup_dir),
        "critical_files_preserved": list(CRITICAL_FILES),
        "moves": [
            {
                "source": str(src),
                "destination": str(dest),
                "type": "file" if src.is_file() else "directory",
            }
            for src, dest in moves
        ],
        "statistics": stats,
    }
    
    with open(log_file, "w") as f:
        json.dump(log_data, f, indent=2)
    
    return log_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Safely migrate non-critical files from data/ to docs/data_bkup/"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Source data directory (default: data)",
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=Path("docs/data_bkup"),
        help="Destination backup directory (default: docs/data_bkup)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be moved without actually moving files",
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
    backup_dir = args.backup_dir.resolve()
    
    # Validate directories
    if not data_dir.exists():
        LOGGER.error("Data directory does not exist: %s", data_dir)
        return 1
    
    if not data_dir.is_dir():
        LOGGER.error("Data path is not a directory: %s", data_dir)
        return 1
    
    # Create backup directory if it doesn't exist
    if not args.dry_run:
        backup_dir.mkdir(parents=True, exist_ok=True)
    
    LOGGER.info("=" * 60)
    LOGGER.info("Data Migration Script")
    LOGGER.info("=" * 60)
    LOGGER.info("Source: %s", data_dir)
    LOGGER.info("Destination: %s", backup_dir)
    LOGGER.info("Mode: %s", "DRY RUN" if args.dry_run else "LIVE")
    LOGGER.info("")
    
    # Verify critical files exist
    LOGGER.info("Critical files that will be preserved:")
    for critical_file in CRITICAL_FILES:
        critical_path = data_dir / critical_file
        if critical_path.exists():
            LOGGER.info("  ✓ %s", critical_file)
        else:
            LOGGER.warning("  ✗ %s (not found!)", critical_file)
    LOGGER.info("")
    
    # Find files to move
    LOGGER.info("Scanning for files to move...")
    moves = find_files_to_move(data_dir, backup_dir)
    
    if not moves:
        LOGGER.info("No files to move.")
        return 0
    
    LOGGER.info("Found %d items to move:", len(moves))
    for src, dest in moves[:10]:  # Show first 10
        LOGGER.info("  - %s -> %s", src.name, dest.relative_to(backup_dir))
    if len(moves) > 10:
        LOGGER.info("  ... and %d more", len(moves) - 10)
    LOGGER.info("")
    
    if args.dry_run:
        LOGGER.info("DRY RUN: No files were actually moved.")
        LOGGER.info("Run without --dry-run to perform the migration.")
        return 0
    
    # Confirm
    response = input("Proceed with migration? (yes/no): ").strip().lower()
    if response not in ("yes", "y"):
        LOGGER.info("Migration cancelled.")
        return 0
    
    # Perform migration
    LOGGER.info("")
    LOGGER.info("Starting migration...")
    stats = move_files(moves, dry_run=False)
    
    # Create migration log
    log_file = create_migration_log(data_dir, backup_dir, moves, stats)
    
    # Summary
    LOGGER.info("")
    LOGGER.info("=" * 60)
    LOGGER.info("Migration Complete")
    LOGGER.info("=" * 60)
    LOGGER.info("Files moved: %d", stats["files_moved"])
    LOGGER.info("Directories moved: %d", stats["dirs_moved"])
    LOGGER.info("Total size: %.2f MB", stats["bytes_moved"] / (1024 * 1024))
    LOGGER.info("Errors: %d", stats["errors"])
    LOGGER.info("Migration log: %s", log_file)
    LOGGER.info("")
    LOGGER.info("Critical files preserved in %s:", data_dir)
    for critical_file in CRITICAL_FILES:
        LOGGER.info("  - %s", critical_file)
    
    return 0 if stats["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

