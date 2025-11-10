# Figure Generation Scripts - November 10, 2025

This folder contains scripts that generate figures for the proposal and report.

## Scripts

### 1. `draw_problem_space.py`
**Purpose:** Generates the problem space visualization (red zone - intersection scale)

**Output:** `docs/figures/problem_space.png`

**Usage:**
```bash
python3 -m src.pax.scripts.draw_problem_space --log-level INFO
```

### 2. `draw_corridor_border.py`
**Purpose:** Generates the camera corridor partition visualization (purple zone - camera zone scale)

**Output:** `docs/figures/camera_corridor_partition.png`

**Usage:**
```bash
python3 -m src.pax.scripts.draw_corridor_border --log-level INFO
```

### 3. `generate_baseline_heatmap.py` (TODO)
**Purpose:** Generate baseline stress score heatmap for all 82 camera zones

**Output:** `docs/figures/baseline_heatmap.png`

### 4. `generate_finegrained_schedule.py` (TODO)
**Purpose:** Generate fine-grained collection schedule diagram

**Output:** `docs/figures/finegrained_schedule.png`

### 5. `generate_astar_flow.py` (TODO)
**Purpose:** Generate A* search algorithm flow diagram

**Output:** `docs/figures/astar_flow.png`

### 6. `generate_pareto_front.py` (TODO)
**Purpose:** Generate Pareto front visualization

**Output:** `docs/figures/pareto_front.png`

### 7. `generate_feature_structure.py` (TODO)
**Purpose:** Generate feature vector structure schema diagram

**Output:** `docs/figures/feature_structure.png`

## Organization

- **Source scripts:** `scripts/2025-11-10/` (this folder)
- **Proposal scripts:** `docs/proposal/scripts/` (copies for proposal)
- **Report scripts:** `docs/report/scripts/` (copies for report)

All scripts should be copied to both proposal and report script directories.

