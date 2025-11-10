# 2025-11-10 Scripts

## Data Organization Scripts

### `migrate_data_to_backup.py`
Safely moves non-critical files from `data/` to `docs/backup/data_bkup/`.
- Preserves critical files (manifests, intersections)
- Handles duplicates
- Creates migration log
- Dry-run mode available

### `organize_data_files.py`
Organizes active data files into subdirectories:
- `data/manifests/` - Camera manifests and image manifests
- `data/geojson/` - GeoJSON files (polygons, zones, cameras, intersections)
- `data/polygons/` - Polygon data (if needed)

### `MIGRATION_README.md`
Documentation for the data migration and organization process.

## Usage

These scripts were used to:
1. Migrate old files to backup
2. Organize active files into logical subdirectories
3. Clean up root `data/` directory

All critical files are now properly organized and referenced paths have been updated throughout the codebase.
