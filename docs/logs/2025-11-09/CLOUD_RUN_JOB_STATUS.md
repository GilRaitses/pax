# Cloud Run Job Status - November 9, 2025

## Job Configuration

**Job Name:** `pax-collector`  
**Project:** `pax-nyc`  
**Region:** `us-central1`  
**Status:** ✅ Active

### Job Details
- **Image:** `gcr.io/pax-nyc/pax-collector`
- **Memory:** 512Mi
- **CPU:** 1000m
- **Task Timeout:** 10 minutes
- **Max Retries:** 3
- **Service Account:** `pax-collector@pax-nyc.iam.gserviceaccount.com`

### Environment Variables
- `PAX_REMOTE_PROVIDER`: `gcs`
- `PAX_REMOTE_BUCKET`: `pax-nyc-images`
- `PAX_REMOTE_PREFIX`: `images`

## Scheduler Status

**Scheduler Name:** `pax-collector-schedule`  
**State:** ✅ **ENABLED**  
**Schedule:** `*/30 * * * *` (every 30 minutes, UTC)  
**Timezone:** UTC

### Scheduler Details
- **Last Attempt:** `2025-11-10T00:00:03.583325Z` (Nov 9, 8:00 PM EST / Nov 10, 00:00 UTC)
- **Next Run:** `2025-11-10T00:30:02.720528Z` (Nov 9, 8:30 PM EST / Nov 10, 00:30 UTC)
- **Topic:** `projects/pax-nyc/topics/run-jobs-trigger`

## Execution History

### Last Execution
- **Execution ID:** `pax-collector-vnmhx`
- **Created:** `2025-11-05T23:02:14.607859Z` (Nov 5, 7:02 PM EST)
- **Status:** ✅ **Completed successfully**
- **Duration:** 1 minute 16 seconds
- **Tasks:** 1/1 completed

### Problem Identified

⚠️ **ISSUE:** Only **ONE execution** has ever run (Nov 5), despite scheduler being enabled and set to run every 30 minutes.

**Expected:** Should have run ~192 times since Nov 5 (every 30 minutes for 4 days = ~192 executions)

**Actual:** Only 1 execution on Nov 5

## Analysis

The scheduler is **ENABLED** and configured correctly, but:
1. Only one execution has occurred (Nov 5)
2. No executions since Nov 5 despite scheduler showing "last attempt" as Nov 10 00:00 UTC
3. The "last attempt" timestamp suggests the scheduler is trying to trigger, but jobs aren't being created

### Possible Causes

1. **Pub/Sub Topic Issue:** The scheduler publishes to `run-jobs-trigger` topic, but Cloud Run job may not be subscribed
2. **Service Account Permissions:** The service account may lack permissions to trigger Cloud Run jobs
3. **Job Subscription:** Cloud Run job may not be properly subscribed to the Pub/Sub topic
4. **Scheduler Configuration:** The scheduler may be configured but not actually triggering

## Next Steps

1. **Check Pub/Sub subscription:**
   ```bash
   gcloud pubsub subscriptions list --project pax-nyc
   ```

2. **Manually trigger job to test:**
   ```bash
   gcloud run jobs execute pax-collector --region us-central1 --project pax-nyc
   ```

3. **Check service account permissions:**
   ```bash
   gcloud projects get-iam-policy pax-nyc --flatten="bindings[].members" --filter="bindings.members:serviceAccount:pax-collector@pax-nyc.iam.gserviceaccount.com"
   ```

4. **Review scheduler logs** for errors:
   ```bash
   gcloud logging read "resource.type=cloud_scheduler_job AND resource.labels.job_id=pax-collector-schedule" --project pax-nyc --limit 50
   ```

5. **Check Cloud Run job logs** for any errors:
   ```bash
   gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=pax-collector" --project pax-nyc --limit 50
   ```

## Summary

- ✅ Job is configured correctly
- ✅ Scheduler is enabled
- ❌ **Job is not executing automatically** (only ran once on Nov 5)
- ⚠️ Missing 4 days of collections (Nov 6-9)

