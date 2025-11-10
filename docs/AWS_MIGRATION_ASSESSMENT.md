# AWS Migration Assessment - November 10, 2025

## Current Issue

Cloud Scheduler missed the 12:30 PM ET collection run. Need to assess if migration to AWS is necessary.

## Cost-Benefit Analysis

### Current GCP Setup

**Costs:**
- Cloud Run: ~$0.40/month (minimal usage)
- Cloud Scheduler: Free
- GCS Storage: ~$0.11/month
- **Total: ~$0.51/month**

**Reliability:**
- ✅ Most runs succeed (2/3 today)
- ❌ Occasional missed runs
- ⚠️  No guarantee of exact timing

**Effort:**
- ✅ Already deployed
- ✅ Working (mostly)
- ✅ No migration needed

### AWS Alternative Setup

**Costs:**
- Lambda: ~$0.20/month (1M requests free tier)
- EventBridge: Free (first 14M custom events)
- S3 Storage: ~$0.023/GB/month (~$0.12/month)
- **Total: ~$0.32/month** (slightly cheaper)

**Reliability:**
- ✅ More reliable than Cloud Scheduler
- ✅ Better monitoring and logging
- ✅ More precise timing
- ✅ Better error handling

**Effort:**
- ❌ Need to rewrite deployment scripts
- ❌ Need to migrate GCS → S3
- ❌ Need to rewrite Cloud Run → Lambda
- ❌ Need to set up new IAM roles
- ❌ Need to update all scripts referencing GCS
- **Estimated: 2-3 days of work**

## Migration Complexity

### What Needs to Change

1. **Storage:**
   - GCS bucket → S3 bucket
   - Update all `gsutil` commands → `aws s3`
   - Update Python code using `google-cloud-storage` → `boto3`

2. **Compute:**
   - Cloud Run Job → Lambda function
   - Rewrite deployment script
   - Update container/image handling

3. **Scheduling:**
   - Cloud Scheduler → EventBridge (Scheduler)
   - Rewrite scheduler configuration
   - Update IAM permissions

4. **Scripts:**
   - Update all scripts referencing GCS
   - Update `generate_gcs_stats.py` → S3 equivalent
   - Update `package_daily_images.py` → S3 equivalent
   - Update `check_gcs_status.py` → S3 equivalent

5. **Documentation:**
   - Update all docs referencing GCP
   - Update deployment guides
   - Update daily protocol

### Estimated Migration Time

- **Storage Migration:** 1 day
- **Compute Migration:** 1 day
- **Scheduler Setup:** 0.5 days
- **Testing & Validation:** 0.5 days
- **Total: ~3 days**

## Recommendation

### Short Term (This Week)

**DO NOT migrate to AWS yet.** Instead:

1. **Implement Monitoring:**
   - Set up Cloud Monitoring alerts for missed runs
   - Create a health check script that verifies collections ran
   - Log all execution attempts

2. **Add Redundancy:**
   - Increase collection frequency to every 15 minutes (more chances)
   - Add a daily manual backup trigger
   - Implement retry logic in the collection script

3. **Investigate Root Cause:**
   - Check if executions are overlapping
   - Verify task timeout settings
   - Check for quota limits

### Medium Term (Next 2 Weeks)

**Monitor and Evaluate:**

1. **Track Reliability:**
   - Log all scheduled runs
   - Calculate success rate
   - Identify patterns in missed runs

2. **If Reliability < 95%:**
   - Consider AWS migration
   - Or implement self-hosted cron on EC2
   - Or use GitHub Actions workflows

### Long Term (If Issues Persist)

**Migration Decision Criteria:**

**Migrate to AWS if:**
- ❌ Success rate drops below 95%
- ❌ More than 1 missed run per day
- ❌ Data collection becomes critical path
- ❌ Current reliability unacceptable for project needs

**Stay with GCP if:**
- ✅ Success rate stays above 95%
- ✅ Occasional missed runs are acceptable
- ✅ Can implement workarounds
- ✅ Migration effort not justified

## Alternative Solutions (Without Full Migration)

### Option 1: Hybrid Approach
- Keep GCS for storage (working fine)
- Use AWS EventBridge just for scheduling
- Lambda function calls GCS API
- **Effort: ~1 day**

### Option 2: Self-Hosted Cron
- Deploy a small EC2 instance
- Run cron job that triggers Cloud Run
- **Effort: ~0.5 days**
- **Cost: ~$5/month** (t2.micro)

### Option 3: GitHub Actions
- Use GitHub Actions scheduled workflows
- Trigger Cloud Run via HTTP
- **Effort: ~0.5 days**
- **Cost: Free** (for public repos)

### Option 4: Improve GCP Reliability
- Add monitoring and alerts
- Implement retry logic
- Increase collection frequency
- **Effort: ~1 day**
- **Cost: No change**

## Conclusion

**Current Assessment:** 
- Migration to AWS is **NOT NECESSARY** at this time
- One missed run does not justify 3 days of migration work
- GCP system is mostly working (67% success rate today, but small sample)

**Recommended Action Plan:**
1. ✅ Implement monitoring (today)
2. ✅ Add retry/backup logic (this week)
3. ⏳ Monitor for 1 week
4. ⏳ Re-evaluate based on reliability data

**Migration Threshold:**
- If success rate drops below 95% over 1 week → Consider migration
- If more than 1 run missed per day → Consider migration
- Otherwise → Stay with GCP and improve monitoring

