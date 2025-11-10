# Data Directory Organization - November 10, 2025

## Summary

Completed two-step data organization:
1. **Migration to Backup**: Moved old/unused files to `docs/data_bkup/`
2. **Organization**: Organized remaining active files into logical subdirectories

## Step 1: Migration to Backup

**Script:** `scripts/migrate_data_to_backup.py`

**Results:**
- ✅ Moved 16 files + 5 directories to `docs/data_bkup/`
- ✅ Preserved 3 critical files in root `data/`
- ✅ Total size moved: 1.18 MB
- ✅ Migration log: `docs/data_bkup/migration_log_20251110_111035.json`

**Critical Files Preserved (root `data/`):**
- `corridor_cameras_numbered.json` - Used by deployment, Cloud Run, stats, index.html
- `corridor_cameras_numbered.yaml` - Same
- `actual_intersections.json` - Used by visualization scripts

**Files Moved to Backup:**
- Old camera manifests (corridor_108_cameras.json, corridor_88_cameras.json, etc.)
- Voronoi zone data directory (`data/voronoi/`)
- Old image organization (`images_by_intersection/`)
- Raw/processed data directories
- Other non-critical JSON/YAML files

## Step 2: Organization

**Script:** `scripts/organize_data_files.py`

**New Structure:**
```
data/
├── actual_intersections.json          # Critical (visualization)
├── corridor_cameras_numbered.json     # Critical (deployment)
├── corridor_cameras_numbered.yaml     # Critical (deployment)
├── manifests/                         # Camera manifests
│   ├── corridor_88_cameras.json
│   ├── corridor_cameras.json
│   ├── corridor_cameras.yaml
│   └── image_manifest.yaml
├── geojson/                           # GeoJSON files
│   ├── corridor_cameras.geojson
│   ├── corridor_polygon.geojson
│   └── voronoi_zones.geojson
└── polygons/                           # Boundary polygons (empty, ready)
```

**Files Copied Back from Backup:**
- Needed files were copied from `docs/data_bkup/` to organized subdirectories
- These files are still needed by scripts but don't need to be in root

## Step 3: Script Path Updates

**Scripts Updated (16 references):**

1. `src/pax/scripts/build_voronoi_zones.py`
   - `data/corridor_cameras.yaml` → `data/manifests/corridor_cameras.yaml`
   - `data/corridor_polygon.geojson` → `data/geojson/corridor_polygon.geojson`
   - `data/voronoi_zones.geojson` → `data/geojson/voronoi_zones.geojson`
   - `data/corridor_cameras.geojson` → `data/geojson/corridor_cameras.geojson`

2. `src/pax/scripts/build_corridor_manifest.py`
   - `data/corridor_cameras.yaml` → `data/manifests/corridor_cameras.yaml`
   - `data/corridor_cameras.json` → `data/manifests/corridor_cameras.json`
   - `data/corridor_polygon.geojson` → `data/geojson/corridor_polygon.geojson`

3. `src/pax/scripts/create_google_maps_viewer.py`
   - `data/voronoi_zones.geojson` → `data/geojson/voronoi_zones.geojson`

4. `src/pax/scripts/download_images.py`
   - `data/image_manifest.yaml` → `data/manifests/image_manifest.yaml`

5. `src/pax/scripts/organize_local_images.py`
   - `data/image_manifest.yaml` → `data/manifests/image_manifest.yaml`

6. `src/pax/scripts/plot_voronoi_map.py`
   - `data/voronoi_zones.geojson` → `data/geojson/voronoi_zones.geojson`
   - `data/corridor_cameras.geojson` → `data/geojson/corridor_cameras.geojson`
   - `data/corridor_polygon.geojson` → `data/geojson/corridor_polygon.geojson`

7. `src/pax/scripts/draw_corridor_border.py`
   - `data/corridor_88_cameras.json` → `data/manifests/corridor_88_cameras.json`

8. `src/pax/scripts/draw_corridor_border_cropped.py`
   - `data/corridor_88_cameras.json` → `data/manifests/corridor_88_cameras.json`

9. `src/pax/scripts/voronoi_stress_scoring.py`
   - `data/voronoi_zones/voronoi_zones.geojson` → `data/geojson/voronoi_zones.geojson`

## Notes

**Scripts Still Using `data/voronoi_zones/` Directory:**
These scripts use `data/voronoi_zones/` as an **OUTPUT** directory (will be created when scripts run):
- `visualize_voronoi_map.py` - Outputs to `data/voronoi_zones/voronoi_tessellation_map.png`
- `create_camera_selector.py` - Outputs to `data/voronoi_zones/camera_selector.html`
- `generate_voronoi_zones.py` - Outputs to `data/voronoi_zones/` subdirectories
- `fetch_expanded_corridor_cameras.py` - Outputs to `data/voronoi_zones/expanded_34th_66th/`
- `select_cameras_from_zones.py` - Outputs to `data/voronoi_zones/selected/`
- `extract_real_intersections.py` - Outputs to `data/voronoi_zones/real_intersections.json`

These are fine - they create the directory structure when they run.

## Benefits

1. **Cleaner Root Directory**: Only 3 critical files in root `data/`
2. **Better Organization**: Files grouped by type (manifests, geojson, polygons)
3. **Easier Maintenance**: Clear separation between active and archived files
4. **Backward Compatible**: Scripts updated to use new paths
5. **Safe**: All changes logged and reversible via migration log

## Migration Log

See: `docs/data_bkup/migration_log_20251110_111035.json` for complete details of what was moved.

