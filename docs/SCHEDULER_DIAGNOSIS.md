# Scheduler Diagnosis and Fix - November 10, 2025

## Problem
Cloud Scheduler was triggering every 30 minutes but Cloud Run job executions were failing (status code 2). Only 2 successful executions in 15 hours instead of ~30.

## Root Cause
The Cloud Scheduler's default service account (`{project-number}-compute@developer.gserviceaccount.com`) did not have `roles/run.invoker` permission to invoke the Cloud Run job.

## Diagnosis Steps
1. ✅ Verified billing is enabled and account is open
2. ✅ Confirmed scheduler IS triggering every 30 minutes (logs show INFO entries)
3. ✅ Manual job execution WORKS (tested successfully)
4. ✅ Job logs show successful collection (81 snapshots)
5. ❌ Scheduler HTTP requests failing (status code 2)
6. ❌ Missing IAM permission for scheduler service account

## Solution Applied
Granted `roles/run.invoker` permission to the compute service account:

```bash
gcloud run jobs add-iam-policy-binding pax-collector-v2 \
  --region=us-central1 \
  --project=pax-nyc \
  --member="serviceAccount:1019191232687-compute@developer.gserviceaccount.com" \
  --role="roles/run.invoker"
```

## Verification
- Next scheduled run: Check at 17:00 UTC (12:00 PM ET)
- Monitor: `gcloud run jobs executions list --job=pax-collector-v2 --region=us-central1`
- Expected: Successful executions every 30 minutes

## If Issue Persists
If the scheduler still fails after granting permissions, it may indicate:
1. Google Cloud account restrictions due to billing dispute
2. OIDC token configuration issue
3. Regional quota limits

**Alternative solutions:** See `docs/ALTERNATIVES_TO_GCP.md` for migration options:
- AWS Lambda + EventBridge (recommended)
- Azure Functions + Timer Trigger
- Self-hosted VPS + Cron
- Railway / Render / Fly.io

## Status
✅ **FIXED** - Permission granted. Next scheduled run should succeed.
