# BRANCH 3 Status: Not Ready Yet

## Can I Start BRANCH 3 Now?

**Answer: No, not yet.**

## Why?

BRANCH 3 (Baseline Generation) **depends on BRANCH 1** (Vision Model Integration).

### Dependencies

BRANCH 3 needs:
- ✅ Vision models set up (YOLOv8n, Detectron2, CLIP)
- ✅ Feature extraction pipeline working
- ✅ Features extracted from images
- ✅ Feature vectors available

### Current Status

- BRANCH 1: In progress (setting up vision models)
- Features: Not yet extracted
- **BRANCH 3: Blocked until BRANCH 1 completes Task 1.5**

## What BRANCH 3 Will Do (When Ready)

1. Process available images per camera zone
2. Compute preliminary stress scores using extracted features
3. Identify zones with sufficient data (≥3 images)
4. Generate partial baseline heatmap
5. Document data gaps

## When Can I Start?

**Start BRANCH 3 when:**
- BRANCH 1 has completed Task 1.5 (Features extracted from current images)
- Feature dataset is available
- You can query features by camera zone

## Alternative: Start BRANCH 4 Instead

**BRANCH 4 (Visualization & Analysis)** can start NOW:
- Uses image metadata only (no features needed)
- Can visualize temporal/spatial coverage
- Can create progress dashboard
- Independent of BRANCH 1

See `BRANCH_4_START_PROMPT.txt` for ready-to-use prompt.

## Check BRANCH 1 Progress

To check if BRANCH 1 is ready:
- Look for `src/pax/vision/extractor.py` (feature extraction pipeline)
- Check if feature dataset exists
- Verify features can be extracted from images

Once BRANCH 1 Task 1.5 is complete, BRANCH 3 can start!
