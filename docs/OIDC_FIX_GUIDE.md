# OIDC Authentication Fix Guide

## Problem
Cloud Scheduler HTTP requests to Cloud Run Job are failing with 401 Unauthorized (OIDC authentication failure).

## Step-by-Step Fix Attempts

### Step 1: Verify Service Account Permissions

**Check if compute service account has run.invoker permission:**

```bash
# Get the compute service account email
PROJECT_NUMBER=$(gcloud projects describe pax-nyc --format='value(projectNumber)')
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
echo "Compute Service Account: $COMPUTE_SA"

# Check IAM policy for the Cloud Run job
gcloud run jobs get-iam-policy pax-collector \
  --region=us-central1 \
  --project=pax-nyc
```

**Expected:** You should see `roles/run.invoker` granted to `serviceAccount:$COMPUTE_SA`

**If missing, grant it:**

```bash
gcloud run jobs add-iam-policy-binding pax-collector \
  --region=us-central1 \
  --project=pax-nyc \
  --member="serviceAccount:$COMPUTE_SA" \
  --role="roles/run.invoker"
```

### Step 2: Verify Service Account Can Create OIDC Tokens

**The compute service account needs permission to create OIDC tokens:**

```bash
# Grant serviceAccountTokenCreator role
gcloud projects add-iam-policy-binding pax-nyc \
  --member="serviceAccount:$COMPUTE_SA" \
  --role="roles/iam.serviceAccountTokenCreator"
```

**Note:** This allows the service account to create OIDC tokens for itself.

### Step 3: Verify OIDC Configuration Matches Exactly

**Check current scheduler configuration:**

```bash
gcloud scheduler jobs describe pax-collector-schedule \
  --location=us-central1 \
  --project=pax-nyc \
  --format=json | jq '.httpTarget.oidcToken'
```

**Verify:**
- `serviceAccountEmail` should be: `1019191232687-compute@developer.gserviceaccount.com`
- `audience` should be: `https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/pax-nyc/jobs/pax-collector:run`

**If incorrect, update scheduler:**

```bash
JOB_URI="https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/pax-nyc/jobs/pax-collector:run"
PROJECT_NUMBER=$(gcloud projects describe pax-nyc --format='value(projectNumber)')
SCHEDULER_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

gcloud scheduler jobs update http pax-collector-schedule \
  --location=us-central1 \
  --project=pax-nyc \
  --oidc-service-account-email="$SCHEDULER_SA" \
  --oidc-token-audience="$JOB_URI"
```

### Step 4: Wait for IAM Propagation

**IAM changes can take up to 5 minutes to propagate:**

```bash
echo "Waiting 60 seconds for IAM propagation..."
sleep 60
```

### Step 5: Test Scheduler Manually

**Manually trigger scheduler to test:**

```bash
gcloud scheduler jobs run pax-collector-schedule \
  --location=us-central1 \
  --project=pax-nyc
```

**Wait 30 seconds, then check for execution:**

```bash
gcloud run jobs executions list \
  --job=pax-collector \
  --region=us-central1 \
  --project=pax-nyc \
  --limit=1
```

**If execution is created:** ✅ OIDC fix worked!

**If still failing:** Check logs for new error messages.

### Step 6: Check for Additional Required Permissions

**Cloud Run Jobs API might require additional permissions:**

```bash
# Grant Cloud Run Admin role (broader permissions)
gcloud projects add-iam-policy-binding pax-nyc \
  --member="serviceAccount:$COMPUTE_SA" \
  --role="roles/run.admin"

# Or grant Service Account User role
gcloud projects add-iam-policy-binding pax-nyc \
  --member="serviceAccount:$COMPUTE_SA" \
  --role="roles/iam.serviceAccountUser"
```

**Note:** These are broader permissions. Use with caution.

### Step 7: Verify Cloud Run Job Configuration

**Check if Cloud Run job has any special authentication requirements:**

```bash
gcloud run jobs describe pax-collector \
  --region=us-central1 \
  --project=pax-nyc \
  --format=json | jq '.spec.template.spec.serviceAccountName'
```

**The job should use its own service account, not the compute service account.**

### Step 8: Alternative: Use Pub/Sub Instead of Direct HTTP

**If OIDC continues to fail, switch to Pub/Sub trigger:**

```bash
# Create Pub/Sub topic
gcloud pubsub topics create run-jobs-trigger --project=pax-nyc

# Update scheduler to publish to Pub/Sub
gcloud scheduler jobs update pubsub pax-collector-schedule \
  --location=us-central1 \
  --project=pax-nyc \
  --schedule="*/30 * * * *" \
  --topic=run-jobs-trigger \
  --message-body='{"job":"pax-collector"}'

# Create Cloud Run service that subscribes to Pub/Sub and triggers job
# (This requires creating a new Cloud Run service, not covered here)
```

**Note:** This is more complex but more reliable.

## Diagnostic Commands

### Check Scheduler Logs for Detailed Errors

```bash
gcloud logging read \
  "resource.type=cloud_scheduler_job AND resource.labels.job_id=pax-collector-schedule" \
  --limit=10 \
  --project=pax-nyc \
  --format=json | jq '.[] | {timestamp, jsonPayload}'
```

### Check Service Account Permissions

```bash
# List all IAM bindings for compute service account
gcloud projects get-iam-policy pax-nyc \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:$COMPUTE_SA" \
  --format="table(bindings.role)"
```

### Test OIDC Token Manually

```bash
# This is complex - requires generating OIDC token manually
# Usually not necessary, but can help debug
```

## Expected Results After Fix

1. ✅ Scheduler triggers successfully
2. ✅ Cloud Run job execution is created
3. ✅ Execution completes successfully
4. ✅ Images are collected

## If All Steps Fail

**After trying all steps above, if OIDC still fails:**

1. **Document the exact error** from scheduler logs
2. **Check GCP Status Page** for service issues
3. **Contact GCP Support** (if you have support)
4. **Consider AWS Migration** (see `docs/AWS_MIGRATION_ASSESSMENT.md`)

## Quick Fix Script

Save this as `fix_oidc.sh` and run it:

```bash
#!/bin/bash
set -e

PROJECT="pax-nyc"
REGION="us-central1"
JOB_NAME="pax-collector"
SCHEDULER_NAME="pax-collector-schedule"

echo "Step 1: Get compute service account"
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
echo "Compute SA: $COMPUTE_SA"

echo "Step 2: Grant run.invoker permission"
gcloud run jobs add-iam-policy-binding "$JOB_NAME" \
  --region="$REGION" \
  --project="$PROJECT" \
  --member="serviceAccount:$COMPUTE_SA" \
  --role="roles/run.invoker" \
  --quiet

echo "Step 3: Grant serviceAccountTokenCreator permission"
gcloud projects add-iam-policy-binding "$PROJECT" \
  --member="serviceAccount:$COMPUTE_SA" \
  --role="roles/iam.serviceAccountTokenCreator" \
  --quiet

echo "Step 4: Verify scheduler OIDC configuration"
JOB_URI="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT}/jobs/${JOB_NAME}:run"
gcloud scheduler jobs update http "$SCHEDULER_NAME" \
  --location="$REGION" \
  --project="$PROJECT" \
  --oidc-service-account-email="$COMPUTE_SA" \
  --oidc-token-audience="$JOB_URI" \
  --quiet

echo "Step 5: Wait for IAM propagation"
sleep 60

echo "Step 6: Test scheduler"
gcloud scheduler jobs run "$SCHEDULER_NAME" \
  --location="$REGION" \
  --project="$PROJECT"

echo "Waiting 30 seconds for execution..."
sleep 30

echo "Checking for execution:"
gcloud run jobs executions list \
  --job="$JOB_NAME" \
  --region="$REGION" \
  --project="$PROJECT" \
  --limit=1

echo "Done! Check the execution status above."
```

