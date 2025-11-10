# Deployment Instructions - Collector v2 with Daily Reminders

## Overview

Deploy the collector with:
- ✅ Numbered camera manifest (82 cameras, matching partitioning map)
- ✅ Collection every 30 minutes (48 images/day per camera)
- ✅ Daily email reminders (8 AM UTC / 3 AM EST)
- ✅ Daily image packaging script

## Prerequisites

1. **Install dependencies** (if not already installed):
   ```bash
   pip install pydantic google-cloud-storage
   ```

2. **Generate numbered manifest** (optional, script does this automatically):
   ```bash
   python3 -m src.pax.scripts.generate_numbered_camera_manifest \
     --output data/corridor_cameras_numbered.json
   ```

## Deployment Steps

### Option 1: Deploy Everything Together (Recommended)

```bash
cd infra/cloudrun
./deploy_with_reminders.sh \
  --project pax-nyc \
  --region us-central1 \
  --bucket pax-nyc-images \
  --email gilraitses@gmail.com
```

This will:
1. Deploy collector v2
2. Deploy email reminder Cloud Function
3. Set up daily reminder scheduler

### Option 2: Deploy Separately

**Step 1: Deploy Collector**
```bash
cd infra/cloudrun
./deploy_collector_v2.sh \
  --project pax-nyc \
  --region us-central1 \
  --bucket pax-nyc-images
```

**Step 2: Set up Email Reminders** (requires Cloud Function deployment)
- See `infra/cloudrun/send_daily_reminder.py` for Cloud Function code
- Deploy manually or use Cloud Console

## Daily Image Packaging

### Package Images from a Specific Date

```bash
python3 -m src.pax.scripts.package_daily_images \
  --bucket pax-nyc-images \
  --date 2025-11-10 \
  --format zip
```

### Package Yesterday's Images (Default)

```bash
python3 -m src.pax.scripts.package_daily_images \
  --bucket pax-nyc-images \
  --format zip
```

### Output

Creates:
- `data/packages/pax-images-YYYY-MM-DD.zip` - Archive with all images
- `data/packages/manifest-YYYY-MM-DD.json` - Metadata about the package

Archive structure:
```
pax-images-2025-11-10.zip
├── 2025-11-10/
│   ├── camera-id-1/
│   │   ├── 20251110T000030.jpg
│   │   ├── 20251110T003000.jpg
│   │   └── ... (48 images)
│   ├── camera-id-2/
│   │   └── ... (48 images)
│   └── ... (82 cameras)
```

## Email Reminders

### What You'll Receive

Every day at 8 AM UTC (3 AM EST), you'll get an email with:
- Summary of images collected yesterday
- Total images, cameras, average per camera
- Instructions to download/package images
- Direct download commands

### Email Configuration

The reminder function needs:
- `REMINDER_EMAIL` environment variable (your email)
- `SENDGRID_API_KEY` (optional, for SendGrid) OR
- `SMTP_USER` and `SMTP_PASSWORD` (for SMTP)

## Manual Collection Check

### Check Today's Collection Status

```bash
# Count images collected today
gsutil ls gs://pax-nyc-images/images/**/*.jpg | grep "$(date +%Y%m%d)" | wc -l

# Check specific camera
gsutil ls gs://pax-nyc-images/images/{camera-id}/*.jpg | grep "$(date +%Y%m%d)" | wc -l
```

### Check Job Executions

```bash
gcloud run jobs executions list \
  --project pax-nyc \
  --region us-central1 \
  --limit 10
```

## Troubleshooting

### Manifest Generation Fails

If manifest generation fails due to missing dependencies:
```bash
pip install pydantic geopandas shapely requests
```

### Email Not Sending

1. Check Cloud Function logs:
   ```bash
   gcloud functions logs read pax-daily-reminder --project pax-nyc --limit 50
   ```

2. Verify email configuration in function environment variables

3. Test function manually:
   ```bash
   curl $(gcloud functions describe pax-daily-reminder --project pax-nyc --region us-central1 --format="value(httpsTrigger.url)")
   ```

## Files Created

- `src/pax/scripts/package_daily_images.py` - Daily packaging script
- `infra/cloudrun/send_daily_reminder.py` - Email reminder Cloud Function
- `infra/cloudrun/deploy_with_reminders.sh` - Combined deployment script

## Next Steps After Deployment

1. **Wait for first collection** (runs every 30 minutes)
2. **Check GCS bucket** after first execution
3. **Receive first email reminder** next day at 8 AM UTC
4. **Package images** using the packaging script when ready

