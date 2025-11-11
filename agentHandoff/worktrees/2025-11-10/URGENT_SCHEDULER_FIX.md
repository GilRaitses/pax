# 🚨 URGENT: Scheduler Invocation Fix

## Priority: CRITICAL

**Issue:** All scheduler-triggered Cloud Run job executions are failing. Only manual executions succeed.

## Agent Assignment

**PRIMARY AGENT:** Focus on debugging and fixing scheduler invocation issue
**TIMELINE:** TODAY (2-4 hours)

## Task Breakdown

### Task 1: Verify Cloud Run Execution Works (30 min)
- Run `test_single_camera_collection.py` to verify manual execution works
- Confirm Cloud Run job can execute successfully
- Document results

### Task 2: Compare Manual vs Scheduler Invocations (1 hour)
- Run `compare_invocations.py` to analyze differences
- Check Cloud Run logs for scheduler-triggered attempts
- Check Scheduler logs for HTTP request details
- Identify exact failure point

### Task 3: Test Scheduler Trigger Manually (30 min)
- Manually trigger scheduler using `gcloud scheduler jobs run`
- Monitor Cloud Run job executions in real-time
- Capture exact error messages
- Document findings

### Task 4: Implement Health Check Workaround (1 hour)
- Deploy `health_check_collection.py` as Cloud Function
- Schedule to run every 35 minutes
- Verify it detects and fixes missed runs
- Test end-to-end

### Task 5: Fix Root Cause (1-2 hours)
- Based on diagnostic results, implement permanent fix
- Options: Fix OIDC, switch to Pub/Sub, use Cloud Tasks
- Test thoroughly
- Deploy fix

## Success Criteria

1. ✅ Test script confirms Cloud Run execution works
2. ✅ Root cause identified (OIDC, HTTP format, IAM, or endpoint)
3. ✅ Health check workaround deployed and working
4. ✅ Permanent fix implemented and tested
5. ✅ Scheduler-triggered executions now succeed

## Files Created

- `scripts/2025-11-10/test_single_camera_collection.py`
- `scripts/2025-11-10/compare_invocations.py`
- `scripts/2025-11-10/health_check_collection.py`
- `docs/DEBUG_SCHEDULER_INVOCATION.md`
- `agentHandoff/worktrees/SCHEDULER_DEBUG_PRIORITY.md`

## Quick Start

```bash
# Step 1: Test Cloud Run execution
python scripts/2025-11-10/test_single_camera_collection.py

# Step 2: Compare invocations
python scripts/2025-11-10/compare_invocations.py --output debug.json

# Step 3: Manually trigger scheduler
gcloud scheduler jobs run pax-collector-schedule --location us-central1 --project pax-nyc

# Step 4: Check logs
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=pax-collector" --limit=50 --project=pax-nyc

# Step 5: Deploy health check
# (See health_check_collection.py for deployment instructions)
```

## Critical Information

- **Cloud Run Job:** `pax-collector`
- **Scheduler:** `pax-collector-schedule`
- **Project:** `pax-nyc`
- **Region:** `us-central1`
- **Issue:** Scheduler HTTP requests not creating Cloud Run job executions

