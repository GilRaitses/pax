# SCHEDULER DEBUG PRIORITY TASK

## 🚨 CRITICAL ISSUE: Scheduler-Invoked Runs Failing

**Status:** URGENT - All scheduler runs failing, only manual runs succeed

**Evidence:**
- ✅ Manual Cloud Run job executions: SUCCESS
- ❌ Scheduler-triggered Cloud Run job executions: FAILURE
- **Conclusion:** Issue is NOT with Cloud Scheduler, but with Cloud Run job invocation via scheduler

## Problem Statement

Cloud Scheduler is triggering correctly (every 30 minutes), but Cloud Run job executions are NOT being created when invoked by the scheduler. Manual executions work fine.

**Key Observation:** 
- Scheduler HTTP requests are being sent
- Cloud Run job endpoint is receiving requests
- But executions are not being created
- Manual `gcloud run jobs execute` commands work perfectly

## Root Cause Hypothesis

1. **OIDC Authentication Issue:** Scheduler's OIDC token may not be valid for Cloud Run job invocation
2. **HTTP Request Format:** Scheduler's HTTP POST may not match Cloud Run's expected format
3. **IAM Permissions:** Compute service account may have permission but token not being passed correctly
4. **Cloud Run Job API Endpoint:** The endpoint URL may be incorrect or require different authentication

## Debugging Strategy

### Phase 1: Verify Cloud Run Execution Works (IMMEDIATE)

**Task:** Create a test script that collects from a single camera multiple times per minute to verify Cloud Run execution works independently.

**Script:** `scripts/2025-11-10/test_single_camera_collection.py`
- Collects from camera #1 (first camera in manifest)
- Runs every 10 seconds for 1 minute (6 collections)
- Verifies each collection succeeds
- Logs all results

**Purpose:** Confirm Cloud Run job execution works when triggered correctly.

### Phase 2: Compare Manual vs Scheduler Invocations (IMMEDIATE)

**Task:** Compare the exact HTTP requests and responses for manual vs scheduler invocations.

**Actions:**
1. Check Cloud Run job logs for scheduler-triggered attempts
2. Check Cloud Scheduler logs for HTTP request details
3. Compare IAM permissions and OIDC tokens
4. Verify HTTP headers and request body

**Script:** `scripts/2025-11-10/compare_invocations.py`
- Captures manual execution request details
- Captures scheduler execution request details
- Compares differences

### Phase 3: Test Scheduler HTTP Trigger Directly (IMMEDIATE)

**Task:** Manually trigger the scheduler's HTTP endpoint to see exact error.

**Actions:**
1. Use `gcloud scheduler jobs run` to manually trigger scheduler
2. Monitor Cloud Run job executions in real-time
3. Check Cloud Run logs for errors
4. Verify OIDC token is being passed correctly

### Phase 4: Implement Workaround (SHORT TERM)

**Task:** Create a health check script that detects missed runs and triggers manual execution.

**Script:** `scripts/2025-11-10/health_check_collection.py`
- Runs every 35 minutes (after scheduled run)
- Checks if collection happened in last 30 minutes
- If not, triggers manual Cloud Run job execution
- Logs all actions

**Deployment:** Run as Cloud Function or Cloud Run service on schedule.

### Phase 5: Fix Root Cause (MEDIUM TERM)

**Task:** Based on diagnostic results, implement permanent solution.

**Possible Solutions:**
1. Fix OIDC token configuration
2. Change scheduler to use Pub/Sub instead of direct HTTP
3. Update Cloud Run job IAM bindings
4. Change scheduler service account configuration

## Immediate Action Plan

### Step 1: Create Test Script (NOW)
```bash
# Create test script for single camera collection
python scripts/2025-11-10/test_single_camera_collection.py
```

### Step 2: Run Manual Test (NOW)
```bash
# Test manual execution works
gcloud run jobs execute pax-collector --region us-central1 --project pax-nyc
```

### Step 3: Trigger Scheduler Manually (NOW)
```bash
# Manually trigger scheduler to see exact error
gcloud scheduler jobs run pax-collector-schedule --location us-central1 --project pax-nyc
```

### Step 4: Monitor in Real-Time (NOW)
```bash
# Watch for execution creation
watch -n 5 'gcloud run jobs executions list --job=pax-collector --region=us-central1 --project=pax-nyc --limit=1'
```

### Step 5: Check Logs (NOW)
```bash
# Check Cloud Run logs for errors
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=pax-collector" --limit=50 --project=pax-nyc

# Check Scheduler logs
gcloud logging read "resource.type=cloud_scheduler_job AND resource.labels.job_id=pax-collector-schedule" --limit=50 --project=pax-nyc
```

## Files to Create

1. `scripts/2025-11-10/test_single_camera_collection.py` - Test script
2. `scripts/2025-11-10/compare_invocations.py` - Comparison script
3. `scripts/2025-11-10/health_check_collection.py` - Health check workaround
4. `docs/DEBUG_SCHEDULER_INVOCATION.md` - Debug log

## Success Criteria

1. ✅ Test script successfully collects from single camera
2. ✅ Manual execution works (already confirmed)
3. ✅ Scheduler invocation creates Cloud Run job execution
4. ✅ Health check detects and fixes missed runs
5. ✅ Root cause identified and fixed

## Timeline

- **Phase 1-3:** TODAY (2-3 hours)
- **Phase 4:** TODAY-TOMORROW (workaround)
- **Phase 5:** THIS WEEK (permanent fix)

## Agent Assignment

**Primary Agent:** Focus on Phases 1-3 (diagnostics)
**Secondary Agent (if needed):** Focus on Phase 4 (workaround implementation)

## Critical Files

- `infra/cloudrun/deploy_collector.sh` - Deployment script
- `infra/cloudrun/Dockerfile` - Container definition
- `src/pax/scripts/collect_manifest.py` - Collection script
- Cloud Run job: `pax-collector`
- Cloud Scheduler: `pax-collector-schedule`

