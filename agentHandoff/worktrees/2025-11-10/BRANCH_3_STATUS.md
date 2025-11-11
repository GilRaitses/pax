# BRANCH 3 Status: ✅ READY TO START

## Can I Start BRANCH 3 Now?

**Answer: ✅ YES! BRANCH 3 is ready to start.**

## Why?

BRANCH 3 (Baseline Generation) **depends on BRANCH 1** (Vision Model Integration), and **BRANCH 1 is now COMPLETE**.

### Dependencies Status

BRANCH 3 needs:
- ✅ Vision models set up (YOLOv8n, Detectron2, CLIP) - **COMPLETE**
- ✅ Feature extraction pipeline working - **COMPLETE**
- ✅ Features can be extracted from images - **COMPLETE**
- ✅ Feature vectors available - **COMPLETE**
- ✅ Torch installation fixed - **COMPLETE** (November 10, 2025)

### Current Status

- ✅ **BRANCH 1: COMPLETE** (all 5 tasks done)
- ✅ Feature extraction pipeline: `src/pax/vision/extractor.py` exists
- ✅ Vision models: YOLOv8n, Detectron2, CLIP wrappers ready
- ✅ Storage system: BRANCH 5's infrastructure ready
- ✅ Torch dependencies: Fixed and available in venv
- ✅ **BRANCH 3: READY TO START NOW!**

## What BRANCH 3 Will Do

1. Process available images per camera zone (~495 images currently available)
2. Extract features using BRANCH 1's vision models
3. Compute preliminary stress scores using extracted features
4. Identify zones with sufficient data (≥3 images)
5. Generate partial baseline heatmap
6. Document data gaps
7. Continue refining as more data is collected (target: 2 weeks baseline)

## How to Start

**Use the ready-to-use prompt:**
- `agentHandoff/worktrees/BRANCH_3_START_PROMPT.txt`

**Or start with:**
```bash
# Activate venv (torch is installed here)
source venv/bin/activate

# Run stress score computation
python scripts/2025-11-10/compute_stress_scores.py \
  --base-image-dir docs/backup/data_bkup/raw/images

# Or use wrapper script
scripts/2025-11-10/run_with_venv.sh \
  scripts/2025-11-10/compute_stress_scores.py \
  --base-image-dir docs/backup/data_bkup/raw/images
```

## What's Available

- ✅ **BRANCH 1:** Vision models (YOLOv8n, Detectron2, CLIP)
- ✅ **BRANCH 2:** Feature vector schema and validation
- ✅ **BRANCH 5:** Storage and query APIs for features
- ✅ **Images:** ~495 images available, system collecting every 30 minutes
- ✅ **Manifest:** 82 cameras in purple corridor
- ✅ **Infrastructure:** Batch processing, monitoring, quality checks

## Next Steps

1. **Extract features from existing images**
   - Use BRANCH 1's `FeatureExtractor` pipeline
   - Process ~495 images
   - Store features using BRANCH 5's storage system

2. **Compute preliminary stress scores**
   - Use extracted features
   - Calculate per-zone metrics
   - Generate baseline heatmap

3. **Continue as data is collected**
   - System now collecting every 30 minutes
   - Process new images as they arrive
   - Refine baseline scores over time

## Related Branches

- ✅ **BRANCH 1:** Vision Model Integration - COMPLETE
- ✅ **BRANCH 2:** Empirical Data Structure - COMPLETE
- ✅ **BRANCH 4:** Visualization & Analysis - COMPLETE (can visualize baseline)
- ✅ **BRANCH 5:** Infrastructure & Tooling - COMPLETE (ready for feature storage)

**Status:** 🟢 **READY TO START - All dependencies met!**
