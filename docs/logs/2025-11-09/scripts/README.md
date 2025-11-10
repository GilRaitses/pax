# Partition Map Scripts - November 9, 2025

## Overview

This folder contains scripts for generating partition maps at different scales for the undirected graph search problem. These scripts create visualizations showing coverage zones, street grids, and problem space boundaries.

## Scripts

### 1. `problem_space_partition.py` (Master Script)
**Purpose:** Creates the constrained problem space visualization (red zone - intersection scale)

**Scale:** Intersection Scale
- **Boundary:** 40th-61st St, Lex-8th/CPW
- **Focus:** Constrained problem space for graph search
- **Intersections:** 161 nodes
- **Cameras:** Uses cameras from purple corridor for Voronoi tessellation

**Key Features:**
- Deep purple Voronoi tessellation lines
- Street grid with major avenues and cross streets highlighted
- Avenue and street labels on all axes
- START/GOAL markers with connecting lines
- Park labels (Central Park, Bryant Park)
- Clean, publication-ready visualization

**Usage:**
```bash
python3 -m src.pax.scripts.draw_problem_space --log-level INFO
```

**Output:** `docs/problem_space.png`

### 2. `camera_corridor_partition.py`
**Purpose:** Creates the extended camera corridor visualization (purple zone - camera zone scale)

**Scale:** Camera Zone Scale
- **Boundary:** 34th-66th St, 3rd-9th/Amsterdam
- **Focus:** Extended corridor for Pareto front analysis
- **Cameras:** 82 cameras in corridor
- **Problem Space:** Red boundary nested within purple zone

**Key Features:**
- Shows wider camera coverage area
- Numbered camera markers
- Voronoi tessellation for all cameras in corridor
- Problem space boundary shown within corridor
- START/GOAL markers

**Usage:**
```bash
python3 -m src.pax.scripts.draw_corridor_border --log-level INFO
```

**Output:** `docs/voronoi_tessellation_final.png`

## Multi-Scale Resolution System

### Camera Zone Scale (Purple Zone)
- **Purpose:** Extended corridor for Pareto front determination
- **Boundary:** 34th-66th St, 3rd-9th/Amsterdam
- **Cameras:** 82 cameras
- **Use Case:** Multi-scale resolution analysis

### Intersection Scale (Red Zone)
- **Purpose:** Constrained problem space for graph search
- **Boundary:** 40th-61st St, Lex-8th/CPW
- **Intersections:** 161 nodes
- **Use Case:** Focused search space

## Technical Details

### Coordinate Transformations
- Affine transformation applied to align streets horizontally and avenues vertically
- X-axis flipped to correct east/west orientation
- Consistent transformation across all geometries

### Camera Filtering
- Buffer tolerance: 0.0003 degrees (~33 meters)
- Corner tolerance: 0.0005 degrees (~55 meters)
- Explicit boundary and corner checks

### Label Positioning
- Avenue labels: 45° (bottom), -45° (top)
- Street labels: -45° (left), 45° (right)
- Labels positioned to touch axis lines
- Proper offsets to avoid overlap

## Future Enhancements

- Create unified script that can generate visualizations at any scale
- Add configuration files for scale definitions
- Create intersection-scale specific visualization
- Develop comparison visualizations showing all scales together

