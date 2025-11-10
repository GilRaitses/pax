# Deployment Complete - November 9, 2025

## ✅ Successfully Deployed

### Collector v2
- **Job:** `pax-collector-v2`
- **Status:** ✅ Deployed and tested
- **Scheduler:** `pax-collector-v2-schedule` (ENABLED)
- **Schedule:** `*/30 * * * *` (every 30 minutes)
- **Manifest:** 82 cameras (numbered 1-82, matching partitioning map)

### Build Optimization
- **Before:** 37,034 files, 1.4 GiB
- **After:** 488 files, 10.3 MiB
- **Excluded:** docs/, venv/, collected images
- **Created:** `.gcloudignore` to prevent uploading unnecessary files

### Collection Behavior
- **Every 30 minutes:** 1 image from each of 82 cameras = 82 images
- **Per day:** 48 images per camera = 3,936 total images
- **Over 14 days:** 672 images per camera = 55,104 total images
- **Storage:** ~5.38 GB total

## What Was Deployed

1. **Numbered Camera Manifest**
   - `data/corridor_cameras_numbered.json` (20KB)
   - `data/corridor_cameras_numbered.yaml` (14KB)
   - 82 cameras numbered 1-82

2. **Cloud Run Job**
   - Image: `gcr.io/pax-nyc/pax-collector-v2`
   - Uses numbered manifest
   - Collects and uploads to GCS

3. **Cloud Scheduler**
   - Direct HTTP trigger (no Pub/Sub)
   - Runs every 30 minutes
   - Reliable execution

## Next Steps

### 1. Deploy Email Reminders (Optional)

```bash
cd infra/cloudrun
./deploy_reminder.sh pax-nyc us-central1 gilraitses@gmail.com
```

This will:
- Deploy Cloud Function for email reminders
- Set up daily scheduler (8 AM UTC / 3 AM EST)
- Send daily summary of images collected

### 2. Package Daily Images

When ready to download images:

```bash
# Package yesterday's images
python3 -m src.pax.scripts.package_daily_images \
  --bucket pax-nyc-images \
  --format zip

# Package specific date
python3 -m src.pax.scripts.package_daily_images \
  --bucket pax-nyc-images \
  --date 2025-11-10 \
  --format zip
```

### 3. Monitor Collection

```bash
# Check recent executions
gcloud run jobs executions list \
  --project pax-nyc \
  --region us-central1 \
  --limit 10

# Check images in GCS
gsutil ls gs://pax-nyc-images/images/ | wc -l

# Count today's images
gsutil ls gs://pax-nyc-images/images/**/*.jpg | grep "$(date +%Y%m%d)" | wc -l
```

## Verification

✅ **Test execution completed successfully**  
✅ **Scheduler enabled and running**  
✅ **Build optimized (10MB vs 1.4GB)**  
✅ **Manifest includes 82 cameras**  
✅ **No billing blocks**

## Files Created

- `.gcloudignore` - Excludes unnecessary files from builds
- `infra/cloudrun/Dockerfile.v2` - Container definition
- `infra/cloudrun/deploy_reminder.sh` - Email reminder deployment
- `src/pax/scripts/package_daily_images.py` - Daily packaging script
- `data/corridor_cameras_numbered.json` - Numbered camera manifest

## Collection Schedule

The collector will automatically:
- Run every 30 minutes
- Collect from all 82 cameras
- Upload to `gs://pax-nyc-images/images/{camera-id}/{timestamp}.jpg`
- Continue for 2 weeks (or until stopped)

**Collection started: November 9, 2025**

