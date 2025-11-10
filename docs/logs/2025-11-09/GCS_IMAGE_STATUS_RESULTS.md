# GCS Image Status Check Results - November 9, 2025

## Summary

**Checked:** `gs://pax-nyc-images/images/`  
**Check Method:** gcloud CLI  
**Date:** November 9, 2025

## Findings

### Images in GCS
- **Total images:** 87
- **Date with images:** November 5, 2025 only
- **Latest timestamp:** `20251105T230404` (November 5, 2025 at 23:04:04 UTC / 7:04 PM EST)
- **Date range:** Single day (November 5th)

### Missing Days
We are missing images for:
- ❌ **November 6, 2025** (4 days ago)
- ❌ **November 7, 2025** (3 days ago)
- ❌ **November 8, 2025** (2 days ago)
- ❌ **November 9, 2025** (today)

**Total missing days: 4 days**

## Comparison with Local Collection

- **Local batch:** `data/raw/metadata/batch_20251105T221619Z.json`
  - Collected: November 5, 2025 at 22:16:19 UTC
  - Cameras: 91 cameras
  - Images: Local files show `image_remote_uri: null` (not uploaded)

- **GCS bucket:** `gs://pax-nyc-images/images/`
  - Images: 87 images
  - Timestamp: November 5, 2025 at 23:04:04 UTC
  - **Note:** GCS images are from a later collection (23:04) than local batch (22:16)

## Zone Coverage Status

**Cannot verify zone coverage without Python script** (google-cloud-storage not installed)

To check purple/red zone coverage:
1. Install: `pip install google-cloud-storage` (or use virtual environment)
2. Run: `python3 -m src.pax.scripts.check_zone_images_gcs`

Expected:
- **Purple Zone:** 82 cameras (34th-66th St, 3rd-9th/Amsterdam)
- **Red Zone:** Subset of purple zone (40th-61st St, Lex-8th/CPW)

## Next Steps

1. **Run collection for missing days** (Nov 6-9)
   ```bash
   # Check if Cloud Run job is running
   gcloud run jobs list --project pax-nyc --region us-central1
   
   # Or run collection manually
   python3 -m src.pax.scripts.collect --gcs-bucket pax-nyc-images --gcs-prefix images
   ```

2. **Verify Cloud Run scheduler** is running every 30 minutes
   ```bash
   gcloud scheduler jobs describe pax-collector-schedule --project pax-nyc --location us-central1
   ```

3. **Check zone coverage** once google-cloud-storage is available
   - Verify all 82 purple zone cameras have images
   - Verify red zone cameras are covered

## Notes

- GCS has images from a later collection (23:04) than the local batch (22:16)
- This suggests Cloud Run job may have run after the local collection
- Only 87 images in GCS vs 91 cameras in local batch suggests some cameras may not have uploaded successfully
- Need to verify if Cloud Run job is still running and collecting images

