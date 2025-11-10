# Debug: Scheduler Invocation Issue

## Problem

**All scheduler-triggered Cloud Run job executions are failing. Only manual executions succeed.**

## Evidence

- ✅ Manual `gcloud run jobs execute` commands: **SUCCESS**
- ❌ Scheduler-triggered executions: **FAILURE** (no executions created)
- ✅ Scheduler is triggering correctly (every 30 minutes)
- ✅ Cloud Run job exists and is configured correctly

## Root Cause Hypothesis

The issue is likely with **Cloud Run job invocation via HTTP**, not with Cloud Scheduler itself.

### Possible Causes

1. **OIDC Token Issue:**
   - Scheduler's OIDC token may not be valid for Cloud Run job API
   - Token may not have correct audience
   - Token may be expired or malformed

2. **HTTP Request Format:**
   - Scheduler's HTTP POST may not match Cloud Run's expected format
   - Missing required headers
   - Incorrect request body

3. **IAM Permissions:**
   - Compute service account has `roles/run.invoker` but token not being passed
   - OIDC authentication failing silently

4. **Cloud Run Job API Endpoint:**
   - Endpoint URL may be incorrect
   - API version mismatch
   - Regional endpoint issue

## Debugging Steps

### Step 1: Test Cloud Run Execution Works

```bash
# Test manual execution
python scripts/2025-11-10/test_single_camera_collection.py \
  --camera-index 0 \
  --interval 10 \
  --duration 1
```

**Expected:** All 6 collections succeed

### Step 2: Compare Invocations

```bash
# Compare manual vs scheduler invocations
python scripts/2025-11-10/compare_invocations.py \
  --hours 24 \
  --output debug_invocations.json
```

**Expected:** See differences in HTTP requests, IAM tokens, or error messages

### Step 3: Manually Trigger Scheduler

```bash
# Manually trigger scheduler to see exact error
gcloud scheduler jobs run pax-collector-schedule \
  --location us-central1 \
  --project pax-nyc

# Watch for execution creation
watch -n 2 'gcloud run jobs executions list \
  --job=pax-collector \
  --region=us-central1 \
  --project=pax-nyc \
  --limit=1'
```

**Expected:** See if execution is created and what errors occur

### Step 4: Check Logs

```bash
# Check Cloud Run logs for errors
gcloud logging read \
  "resource.type=cloud_run_job AND resource.labels.job_name=pax-collector" \
  --limit=50 \
  --project=pax-nyc \
  --format=json > cloud_run_logs.json

# Check Scheduler logs
gcloud logging read \
  "resource.type=cloud_scheduler_job AND resource.labels.job_id=pax-collector-schedule" \
  --limit=50 \
  --project=pax-nyc \
  --format=json > scheduler_logs.json
```

**Expected:** Find error messages explaining why executions aren't created

### Step 5: Verify Scheduler Configuration

```bash
# Get scheduler details
gcloud scheduler jobs describe pax-collector-schedule \
  --location us-central1 \
  --project pax-nyc \
  --format=json > scheduler_config.json

# Check OIDC configuration
cat scheduler_config.json | jq '.httpTarget.oidcToken'
```

**Expected:** Verify OIDC token configuration is correct

## Workaround: Health Check Script

Until root cause is fixed, use health check script to detect and fix missed runs:

```bash
# Run health check (checks last 35 minutes)
python scripts/2025-11-10/health_check_collection.py \
  --trigger \
  --project pax-nyc \
  --region us-central1 \
  --job pax-collector
```

**Deploy as Cloud Function or Cloud Run service:**
- Schedule: Every 35 minutes (after scheduled run)
- Action: Check for recent collection, trigger manual execution if missed

## Potential Solutions

### Solution 1: Fix OIDC Token Configuration

If OIDC token is the issue:
1. Verify service account has correct permissions
2. Check token audience matches Cloud Run API
3. Regenerate OIDC token

### Solution 2: Switch to Pub/Sub

Instead of direct HTTP, use Pub/Sub:
1. Create Pub/Sub topic
2. Configure Cloud Run job to subscribe to topic
3. Update scheduler to publish to topic

### Solution 3: Use Cloud Run Service Instead of Job

Cloud Run Services may have better scheduler integration:
1. Convert job to service
2. Use Cloud Scheduler HTTP trigger to service endpoint
3. Service handles job execution internally

### Solution 4: Use Cloud Tasks

Cloud Tasks may be more reliable for scheduled job execution:
1. Create Cloud Tasks queue
2. Configure scheduler to create tasks
3. Cloud Run job processes tasks

## Timeline

- **Today:** Complete Steps 1-5 (diagnostics)
- **Today:** Implement health check workaround
- **This Week:** Fix root cause based on diagnostics
- **This Week:** Deploy permanent solution

## Files

- `scripts/2025-11-10/test_single_camera_collection.py` - Test script
- `scripts/2025-11-10/compare_invocations.py` - Comparison script
- `scripts/2025-11-10/health_check_collection.py` - Health check workaround
- `docs/DEBUG_SCHEDULER_INVOCATION.md` - This file

