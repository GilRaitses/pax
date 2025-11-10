# GCS Image Status Check - November 9, 2025

## Summary

Based on local batch manifests, the last collection was:
- **Date:** November 5, 2025
- **Time:** 22:16:19 UTC (6:16 PM EST)
- **Cameras collected:** 91 cameras
- **Batch file:** `data/raw/metadata/batch_20251105T221619Z.json`

## Missing Days

If last pull was 5 days ago (November 4th), we're missing:
- November 5th (if collection didn't complete)
- November 6th
- November 7th  
- November 8th
- November 9th (today)

**Total missing days: 4-5 days**

## Zone Definitions

### Purple Zone (Camera Corridor)
- **Boundary:** 34th-66th St, 3rd-9th/Amsterdam
- **Expected cameras:** 82 cameras
- **Purpose:** Extended corridor for Pareto front analysis

### Red Zone (Problem Space)
- **Boundary:** 40th-61st St, Lex-8th/CPW
- **Expected cameras:** Subset of purple zone cameras
- **Purpose:** Constrained problem space for graph search

## Checking GCS Status

The deployment configuration shows:
- **Bucket:** `pax-nyc-images` (from `infra/cloudrun/deploy.sh`)
- **Prefix:** `images` (default)
- **Project:** `pax-nyc`
- **Region:** `us-central1`

To check what images are actually in GCS for these zones, run:

```bash
# Install google-cloud-storage if needed
pip install google-cloud-storage

# Check GCS status (uses default bucket pax-nyc-images)
python3 -m src.pax.scripts.check_zone_images_gcs

# Or specify bucket explicitly
python3 -m src.pax.scripts.check_zone_images_gcs --bucket pax-nyc-images

# Or use the general GCS status checker
python3 -m src.pax.scripts.check_gcs_status --bucket pax-nyc-images
```

## Script Created

A new script `check_zone_images_gcs.py` has been created to:
1. Fetch all cameras from the API
2. Filter cameras by purple and red zone boundaries
3. Check GCS bucket for images from those cameras
4. Identify date ranges and gaps
5. Report missing dates

## Next Steps

1. **Check GCS bucket** to see what images are actually stored there
2. **Compare with local collections** to identify gaps
3. **Run collection** for missing days if needed
4. **Verify zone coverage** - ensure all 82 purple zone cameras have images

## Notes

- Local batch files show `image_remote_uri: null` for all cameras, suggesting images may not have been uploaded to GCS
- Need to verify if images were uploaded separately or if collection needs to be run with GCS upload enabled

