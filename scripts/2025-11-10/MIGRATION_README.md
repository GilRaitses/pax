# Data Migration Script

## Purpose

The `migrate_data_to_backup.py` script safely migrates non-critical files from the root `data/` directory to `docs/data_bkup/` for archival, while preserving critical files that are actively used by the codebase.

## Critical Files Preserved

These files **must** stay in root `data/` because they're actively referenced:

- `data/corridor_cameras_numbered.json` - Used by deployment scripts, Cloud Run jobs, stats generation, and index.html
- `data/corridor_cameras_numbered.yaml` - Same as above
- `data/geojson/intersections.json` - Used by visualization scripts (`draw_corridor_border.py`, `draw_problem_space.py`)

## Usage

### Dry Run (Recommended First)

See what would be moved without actually moving anything:

```bash
python3 scripts/migrate_data_to_backup.py --dry-run
```

### Perform Migration

Run the actual migration:

```bash
python3 scripts/migrate_data_to_backup.py
```

The script will:
1. Show you what will be moved
2. Ask for confirmation
3. Move files and directories
4. Create a migration log in `docs/data_bkup/migration_log_TIMESTAMP.json`

### Options

```bash
python3 scripts/migrate_data_to_backup.py --help
```

Options:
- `--data-dir PATH` - Source directory (default: `data`)
- `--backup-dir PATH` - Destination directory (default: `docs/data_bkup`)
- `--dry-run` - Show what would be moved without moving
- `--log-level LEVEL` - Logging level (default: INFO)

## What Gets Moved

The script moves:
- Old camera manifest files (corridor_108_cameras.json, etc.)
- Voronoi zone data (can be regenerated)
- Old image organization (`images_by_intersection/`)
- Raw images (already gitignored)
- Processed data (if exists)
- Other non-critical JSON/YAML files

## Safety Features

1. **Preserves critical files** - Never moves the 3 critical files listed above
2. **Handles duplicates** - If a file exists in both locations, keeps the newer one
3. **Creates migration log** - Documents everything that was moved for reversibility
4. **Dry-run mode** - Test before committing
5. **Confirmation prompt** - Asks before proceeding

## Migration Log

After migration, a JSON log file is created in `docs/data_bkup/` with:
- Timestamp
- List of all moves (source → destination)
- Statistics (files moved, bytes moved, errors)
- List of critical files preserved

## Reversibility

The migration log can be used to reverse the migration if needed. The log contains all source and destination paths.

## Notes

- The `.gitignore` already excludes `docs/data_bkup/**`, so moved files won't be committed to git
- Large directories like `data/raw/images/` are already gitignored
- The script preserves directory structure when moving

