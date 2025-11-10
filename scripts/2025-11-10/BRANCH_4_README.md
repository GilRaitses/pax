# BRANCH 4: Visualization & Analysis Scripts

This directory contains scripts for visualizing and analyzing image collection data. All scripts work with image metadata only - no features needed.

## Scripts

### 1. `assess_image_quality.py`
**Purpose:** Assess image quality from manifest and image files.

**Features:**
- Checks image resolution and dimensions
- Calculates brightness and contrast metrics
- Identifies corrupted/missing images
- Generates comprehensive quality report

**Usage:**
```bash
python scripts/2025-11-10/assess_image_quality.py \
    --manifest data/manifests/image_manifest.yaml \
    --images-dir data/raw/images \
    --output-report docs/reports/image_quality_report.md
```

**Output:** `docs/reports/image_quality_report.md`

---

### 2. `visualize_temporal_coverage.py`
**Purpose:** Visualize temporal coverage of image collection.

**Features:**
- Plots images by hour of day (hourly bins)
- Shows collection timeline scatter plot
- Displays daily collection counts
- Creates temporal coverage heatmap
- Identifies coverage gaps and peak collection times

**Usage:**
```bash
python scripts/2025-11-10/visualize_temporal_coverage.py \
    --manifest data/manifests/image_manifest.yaml \
    --output docs/figures/temporal_coverage.png
```

**Output:** `docs/figures/temporal_coverage.png`

---

### 3. `visualize_spatial_coverage.py`
**Purpose:** Visualize spatial coverage of image collection.

**Features:**
- Maps which camera zones have images
- Shows coverage density by image count
- Identifies spatial gaps (zones without images)
- Overlays camera locations and corridor boundaries

**Usage:**
```bash
python scripts/2025-11-10/visualize_spatial_coverage.py \
    --manifest data/manifests/image_manifest.yaml \
    --zones data/geojson/voronoi_zones.geojson \
    --cameras data/geojson/corridor_cameras.geojson \
    --corridor data/geojson/corridor_polygon.geojson \
    --output docs/figures/spatial_coverage.png
```

**Output:** `docs/figures/spatial_coverage.png`

---

### 4. `generate_progress_dashboard.py`
**Purpose:** Generate collection progress dashboard HTML.

**Features:**
- Shows progress toward 2-week goal (672 images/camera)
- Displays images per camera with progress bars
- Shows collection rate trends with interactive charts
- Estimates completion date based on current collection rate
- Interactive HTML dashboard with Chart.js visualizations

**Usage:**
```bash
python scripts/2025-11-10/generate_progress_dashboard.py \
    --manifest data/manifests/image_manifest.yaml \
    --output docs/progress_dashboard.html \
    --goal 672
```

**Output:** `docs/progress_dashboard.html`

**View:** Open `docs/progress_dashboard.html` in a web browser.

---

### 5. `generate_baseline_heatmap.py`
**Purpose:** Generate baseline heatmap visualization from stress scores.

**Features:**
- Supports partial data visualization (zones without stress scores)
- Maps stress scores to Voronoi zones
- Creates heatmap with data availability overlay
- Reusable for future updates as more data becomes available
- Handles missing data gracefully

**Usage:**
```bash
# With stress scores file
python scripts/2025-11-10/generate_baseline_heatmap.py \
    --zones data/geojson/voronoi_zones.geojson \
    --cameras data/geojson/corridor_cameras.geojson \
    --corridor data/geojson/corridor_polygon.geojson \
    --stress-scores data/stress_scores.json \
    --output docs/figures/baseline_heatmap.png

# Without stress scores (uses manifest image counts as placeholder)
python scripts/2025-11-10/generate_baseline_heatmap.py \
    --manifest data/manifests/image_manifest.yaml \
    --output docs/figures/baseline_heatmap.png
```

**Output:** `docs/figures/baseline_heatmap.png`

**Note:** This script will generate a heatmap once stress scores are available. Until then, it can use image counts as a placeholder or show data availability.

---

## Dependencies

All scripts require:
- Python 3.11+
- Standard project dependencies (see `pyproject.toml`)
- Image manifest YAML file
- Spatial data files (GeoJSON) for spatial visualizations

## Output Directories

Scripts will create output directories if they don't exist:
- `docs/reports/` - Quality reports
- `docs/figures/` - Visualization images
- `docs/progress_dashboard.html` - Progress dashboard

## Data Requirements

- **Image Manifest:** `data/manifests/image_manifest.yaml` (required for all scripts)
- **Voronoi Zones:** `data/geojson/voronoi_zones.geojson` (for spatial visualizations)
- **Cameras:** `data/geojson/corridor_cameras.geojson` (for spatial visualizations)
- **Corridor:** `data/geojson/corridor_polygon.geojson` (for spatial visualizations)
- **Stress Scores:** JSON file with `camera_id -> stress_score` mapping (optional, for heatmap)

## Running All Scripts

To run all visualization scripts in sequence:

```bash
# 1. Assess image quality
python scripts/2025-11-10/assess_image_quality.py

# 2. Visualize temporal coverage
python scripts/2025-11-10/visualize_temporal_coverage.py

# 3. Visualize spatial coverage
python scripts/2025-11-10/visualize_spatial_coverage.py

# 4. Generate progress dashboard
python scripts/2025-11-10/generate_progress_dashboard.py

# 5. Generate baseline heatmap (when stress scores available)
python scripts/2025-11-10/generate_baseline_heatmap.py --stress-scores data/stress_scores.json
```

## Notes

- All scripts work with image metadata only - no feature extraction needed
- Scripts handle partial/missing data gracefully
- Output files are overwritten on each run
- Scripts log progress and statistics to console

