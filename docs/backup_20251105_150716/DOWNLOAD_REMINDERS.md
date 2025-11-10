# 6-Hour Download Reminders Setup

## Overview

Get email reminders every 6 hours with direct download links for new files in your GCS bucket. This ensures you can download files before they're auto-deleted by the lifecycle policy.

## Lifecycle Policy

**Updated:** Files are kept for **7 days** (instead of 1 day) to give you time to download them.

You can check/update the lifecycle:
```bash
export PATH="/opt/homebrew/share/google-cloud-sdk/bin:$PATH"
gcloud storage buckets describe gs://pax-nyc-images --project=pax-nyc
```

To change retention period:
```bash
# Update lifecycle.json
cat > /tmp/lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [{
      "action": {"type": "Delete"},
      "condition": {"age": 7}  # Change this number
    }]
  }
}
EOF

gcloud storage buckets update gs://pax-nyc-images \
    --lifecycle-file=/tmp/lifecycle.json \
    --project=pax-nyc
```

## Quick Setup

```bash
cd ~/pax
./setup_6hour_reminders.sh
```

Follow the prompts to configure:
1. Your email address
2. Email provider (Gmail/Outlook/Custom)
3. SMTP password/app password

## Manual Setup

### 1. Get App Password (Gmail)

1. Go to https://myaccount.google.com/apppasswords
2. Create an app password for "Pax NYC Download Reminders"
3. Copy the 16-character password

### 2. Test the Script

```bash
cd ~/pax
source venv/bin/activate

python -m pax.scripts.email_download_reminder \
    --email your.email@gmail.com \
    --smtp-password "your-app-password" \
    --bucket pax-nyc-images \
    --prefix images \
    --hours 6
```

### 3. Setup Cron Job

The setup script creates cron jobs, but you can also do it manually:

```bash
# Edit crontab
crontab -e

# Add these lines (every 6 hours):
0 0,6,12,18 * * * /Users/gilraitses/.pax_6hour_reminder.sh
```

## Email Content

Each reminder includes:

```
Subject: Pax NYC Download Reminder - 12 new files

Recent Files (last 6 hours):
• images/camera-id/timestamp.jpg
  Size: 0.45 MB
  Uploaded: 2025-11-03T18:00:00 UTC
  Download: [signed URL valid for 7 days]

...more files...

Download All:
  gsutil -m cp -r gs://pax-nyc-images/* ./downloads/

Or view in Cloud Console:
  https://console.cloud.google.com/storage/browser/pax-nyc-images
```

## Download Links

Each email includes:
- **Individual download URLs** - Signed URLs valid for 7 days per file
- **Bulk download command** - `gsutil` command to download everything
- **Cloud Console link** - Web interface to browse files

## Schedule

Reminders are sent:
- **00:00** (midnight)
- **06:00** (6 AM)
- **12:00** (noon)
- **18:00** (6 PM)

## File Retention

- **Lifecycle:** 7 days (after which files auto-delete)
- **Download links:** Valid for 7 days
- **Reminders:** Every 6 hours

This gives you multiple chances to download before deletion.

## Troubleshooting

### No files found

If you get "No new files" emails:
- Check that Cloud Run collector is running: `gcloud run jobs executions list --project pax-nyc`
- Verify files are uploading: `gcloud storage ls gsburg://pax-nyc-images/images/`

### Email not sending

Check the log:
```bash
tail -f ~/.pax_download_reminder.log
```

Common issues:
- Invalid SMTP password
- Firewall blocking SMTP port
- Wrong SMTP settings

### Update retention period

Change lifecycle age condition (see above), or disable auto-delete entirely:

```bash
gcloud storage buckets update gs://pax-nyc-images \
    --clear-lifecycle-rules \
    --project=pax-nyc
```

## Disable Reminders

Remove from crontab:
```bash
crontab -e
# Delete the line with pax_6hour_reminder
```

## Alternative: Cloud Scheduler

For cloud-based scheduling (no local cron needed):

```bash
gcloud scheduler jobs create http pax-download-reminder \
    --project=pax-nyc \
    --location=us-east1 \
    --schedule="0 */6 * * *" \
    --uri="https://your-cloud-function-url" \
    --http-method=POST
```

Then create a Cloud Function that calls `email_download_reminder.py`.




