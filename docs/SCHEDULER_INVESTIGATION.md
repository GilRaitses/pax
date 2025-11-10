# Cloud Scheduler Investigation - November 10, 2025

## Issue

12:30 PM ET (17:30 UTC) collection run was missed. No execution found, no images collected.

## Investigation Results

### Scheduler Configuration

- **Schedule:** `*/30 * * * *` (every 30 minutes)
- **Timezone:** UTC
- **State:** ENABLED
- **Expected Runs:** At :00 and :30 of each UTC hour
  - UTC 17:00 = ET 12:00 PM ✅ (executed at 12:01 PM)
  - UTC 17:30 = ET 12:30 PM ❌ (MISSED)
  - UTC 18:00 = ET 01:00 PM (next run)

### Execution Pattern Analysis

**Today's Executions:**
- 11:52 AM ET: ✅ Succeeded
- 12:01 PM ET: ✅ Succeeded (should have been 12:00 PM)
- 12:30 PM ET: ❌ MISSED

**Observations:**
1. Executions are slightly delayed (12:01 instead of 12:00)
2. 12:30 PM run was completely skipped
3. Scheduler is enabled and working (other runs succeed)

### Possible Causes

1. **Scheduler Timing Issues:**
   - Cloud Scheduler has known reliability issues
   - Can miss runs during high load periods
   - No guarantee of exact timing

2. **Execution Overlap:**
   - Previous execution may have been running too long
   - Cloud Run job may have concurrency limits
   - Next run blocked by previous run

3. **Scheduler Limitations:**
   - Cloud Scheduler is not 100% reliable
   - No built-in retry for missed runs
   - No guarantee of execution timing precision

4. **Resource Constraints:**
   - GCP quota limits
   - Service account permissions
   - Network issues

## Assessment: Is AWS Migration Necessary?

### Current Situation

**Pros of Staying with GCP:**
- ✅ System is mostly working (2/3 runs today succeeded)
- ✅ Infrastructure already deployed
- ✅ No migration effort needed
- ✅ Cost-effective for current scale

**Cons of Staying with GCP:**
- ❌ Occasional missed runs (unreliable)
- ❌ No guarantee of execution timing
- ❌ Limited debugging capabilities
- ❌ Scheduler reliability issues documented

### AWS Alternatives

**Option 1: AWS EventBridge (Scheduler)**
- ✅ More reliable than Cloud Scheduler
- ✅ Better monitoring and logging
- ✅ More precise timing
- ❌ Requires migration effort
- ❌ Need to redeploy infrastructure

**Option 2: AWS Lambda + EventBridge**
- ✅ Serverless, similar to Cloud Run
- ✅ More reliable scheduling
- ✅ Better error handling
- ❌ Migration effort
- ❌ Need to rewrite deployment scripts

**Option 3: Self-Hosted Cron (EC2)**
- ✅ Full control
- ✅ 100% reliability (if server is up)
- ❌ Need to manage server
- ❌ Additional cost
- ❌ Single point of failure

**Option 4: GitHub Actions Scheduled Workflows**
- ✅ Free for public repos
- ✅ Reliable scheduling
- ✅ Easy to set up
- ❌ Limited to GitHub repos
- ❌ May have rate limits

### Recommendation

**Short Term (Fix Current Issue):**
1. **Add Retry Logic:** Implement a secondary check/retry mechanism
2. **Monitor More Closely:** Set up alerts for missed runs
3. **Increase Redundancy:** Run collection more frequently (every 15 min instead of 30)
4. **Manual Backup:** Set up a daily manual trigger as backup

**Medium Term (Improve Reliability):**
1. **Implement Health Checks:** Check if collection ran, trigger if missed
2. **Add Monitoring:** Cloud Monitoring alerts for missed runs
3. **Consider Event-Driven:** Use Pub/Sub with retry logic instead of scheduler

**Long Term (If Issues Persist):**
1. **Evaluate AWS Migration:** If >5% of runs are missed, consider AWS
2. **Hybrid Approach:** Keep GCP for storage, use AWS for scheduling
3. **Self-Hosted Option:** If reliability is critical, consider EC2 cron

### Decision Criteria

**Migrate to AWS if:**
- ❌ More than 5% of scheduled runs are missed
- ❌ Critical data collection requirements
- ❌ Need guaranteed execution timing
- ❌ Current reliability unacceptable

**Stay with GCP if:**
- ✅ Occasional missed runs are acceptable
- ✅ Can implement workarounds (retry logic, monitoring)
- ✅ Migration effort not justified
- ✅ Current reliability is acceptable

## Immediate Actions

1. **Monitor Next Few Runs:** Check if 1:00 PM, 1:30 PM runs execute
2. **Check Execution Logs:** Look for errors or timeouts
3. **Verify Scheduler Health:** Check GCP status page for issues
4. **Implement Monitoring:** Set up alerts for missed collections

## Conclusion

**Current Assessment:** GCP Cloud Scheduler has reliability issues, but system is mostly working. Migration to AWS is **NOT NECESSARY** at this time, but should be considered if:
- Missed runs become frequent (>5%)
- Data collection becomes critical path
- Current reliability unacceptable

**Recommendation:** Implement monitoring and retry logic first. Re-evaluate after 1 week of monitoring.

