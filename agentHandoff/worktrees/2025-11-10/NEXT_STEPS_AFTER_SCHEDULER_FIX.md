# Next Steps After Scheduler Fix

**Date:** November 10, 2025  
**Status:** ✅ Scheduler operational, system collecting images every 30 minutes

## Immediate Actions

### 1. Verify Image Collection Completes Manifest

**Status:** ⏳ In Progress
- Execution `pax-collector-2gz87` completed successfully
- Need to verify all 82 cameras collected images
- Check GCS for images from 2:00 PM run

**Action:**
```bash
# Check images from 2:00 PM run
gsutil ls -r gs://pax-nyc-images/images/ | grep "2025-11-10T14" | wc -l

# Should see ~82 images (1 per camera)
```

### 2. Monitor Consistency

**Next Runs:**
- 2:30 PM ET (19:30 UTC)
- 3:00 PM ET (20:00 UTC)
- Continue monitoring for consistency

**Action:**
```bash
# Monitor next run
./scripts/2025-11-10/monitor_next_run.sh
```

## Master TODO: What's Next?

### Phase 1: Baseline Generation & Empirical Structure

#### ✅ 1.1 Define Empirical Data Structure - COMPLETE
- **Status:** ✅ Done (BRANCH 2)
- **Deliverables:** Feature vector schema, validation, documentation

#### 🔄 1.2 Generate Baselines for Camera Zones - READY TO START
- **Status:** Can start now with existing ~495 images
- **Dependencies:** ✅ BRANCH 1 (vision models), ✅ BRANCH 2 (schema), ✅ BRANCH 5 (infrastructure)
- **Action:** Start BRANCH 3

**Tasks:**
- [ ] Extract features from existing images using BRANCH 1's vision models
- [ ] Compute preliminary stress scores per zone
- [ ] Generate partial baseline heatmap
- [ ] Continue as more data is collected (target: 2 weeks)

### Phase 2: Fine-Grained Collection - BLOCKED

**Status:** Waiting for baseline generation (1.2)
**Dependency:** Need baseline scores to identify top/bottom 5 zones

### Phase 3: A* Search Implementation

#### 3.1 Pseudocode & Knowledge Base Design - READY TO START
- **Status:** Can start now (independent of baseline)
- **Action:** Design A* search architecture

**Tasks:**
- [ ] Create pseudocode for baseline A* with Manhattan distance
- [ ] Create pseudocode for learned heuristic A*
- [ ] Design knowledge base structure
- [ ] Document algorithm flow

#### 3.2 Baseline A* Search - READY TO START
- **Status:** Can start now (has intersection network)
- **Dependencies:** ✅ Intersection network (161 intersections)

**Tasks:**
- [ ] Implement graph structure (nodes = intersections, edges = streets)
- [ ] Implement A* algorithm
- [ ] Test with Grand Central → Carnegie Hall
- [ ] Generate baseline path visualization

#### 3.3 Learned Heuristic A* - BLOCKED
- **Status:** Waiting for baseline generation (1.2)
- **Dependency:** Need baseline stress scores to train Ridge regression

#### 3.4 Pareto Front Evaluation - BLOCKED
- **Status:** Waiting for learned heuristic (3.3)
- **Dependency:** Need learned heuristic to compute Pareto front

### Phase 4: AI Agent Design - BLOCKED
- **Status:** Waiting for A* search implementation (Phase 3)

## Agent Branch Next Steps

### ✅ BRANCH 1: Vision Model Integration - COMPLETE
**Status:** All tasks done, ready for use

### ✅ BRANCH 2: Empirical Data Structure - COMPLETE
**Status:** All tasks done, schema ready

### 🔄 BRANCH 3: Baseline Generation - READY TO START
**Status:** Can start now!

**Prompt:** Use `agentHandoff/worktrees/BRANCH_3_START_PROMPT.txt`

**Tasks:**
1. Process existing ~495 images
2. Extract features using BRANCH 1's vision models
3. Compute preliminary stress scores per zone
4. Generate partial baseline heatmap
5. Continue as more data is collected

**Can Use:**
- BRANCH 1's vision models (YOLOv8n, Detectron2, CLIP)
- BRANCH 2's feature vector schema
- BRANCH 5's storage and query APIs

### ✅ BRANCH 4: Visualization & Analysis - COMPLETE
**Status:** All tasks done, ready for baseline visualization

### ✅ BRANCH 5: Infrastructure & Tooling - COMPLETE
**Status:** All tasks done, infrastructure ready

## Recommended Execution Order

### This Week (Nov 10-16)

1. **Verify Collection** (Today)
   - ✅ Confirm 2:00 PM run completed
   - ⏳ Verify all 82 cameras collected
   - ⏳ Monitor 2:30 PM run

2. **Start BRANCH 3: Baseline Generation** (Today/Tomorrow)
   - Process existing ~495 images
   - Extract features
   - Compute preliminary stress scores
   - Generate partial baseline heatmap

3. **Start Phase 3.1: Pseudocode Design** (This Week)
   - Design A* search architecture
   - Design knowledge base structure
   - Document algorithm flow

4. **Start Phase 3.2: Baseline A* Search** (This Week)
   - Implement graph structure
   - Implement A* algorithm
   - Test with Grand Central → Carnegie Hall

### Next Week (Nov 17-23)

1. **Continue Baseline Generation**
   - Process new images as they're collected
   - Refine stress scores
   - Update baseline heatmap

2. **Complete Baseline A* Search**
   - Finish implementation
   - Generate baseline path visualization
   - Document performance metrics

3. **Prepare for Learned Heuristic**
   - Once baseline scores are stable, train Ridge regression
   - Implement learned heuristic A*

## Commands to Run

### Verify Collection
```bash
# Check images from 2:00 PM run
gsutil ls -r gs://pax-nyc-images/images/ | grep "2025-11-10T14" | wc -l

# Monitor next run
./scripts/2025-11-10/monitor_next_run.sh
```

### Start BRANCH 3
```bash
# Process existing images
python scripts/2025-11-10/batch_process_images.py \
  --input-dir data/raw/images \
  --output-dir data/features \
  --format parquet \
  --workers 4

# Monitor extraction
python scripts/2025-11-10/monitor_extraction.py

# Check quality
python scripts/2025-11-10/check_feature_quality.py \
  --input data/features/features.parquet
```

### Query Features by Zone
```python
from src.pax.storage.feature_query import FeatureQuery

query = FeatureQuery("data/features/features.parquet")
zone_features = query.get_by_zone("zone_42")  # Example zone ID
stats = query.get_zone_statistics("zone_42")
```

## Files to Update

- [x] `docs/logs/2025-11-10.md` - Updated with next steps
- [ ] `docs/logs/MASTER_TODO.md` - Update with scheduler resolution
- [ ] `agentHandoff/worktrees/WORK_TREE_STATUS.md` - Update status
- [ ] Create BRANCH 3 progress tracking

---

**Key Point:** System is now operational. We can proceed with baseline generation using existing images while continuing to collect more data for the full 2-week baseline.

