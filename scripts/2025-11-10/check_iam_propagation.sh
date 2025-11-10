#!/bin/bash

PROJECT="pax-nyc"
REGION="us-central1"
JOB_NAME="pax-collector"
SCHEDULER_NAME="pax-collector-schedule"

echo "=========================================="
echo "IAM Propagation Status Check"
echo "=========================================="
echo ""

PROJECT_NUMBER=$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "Compute Service Account: $COMPUTE_SA"
echo ""

# Method 1: Check IAM policy directly (shows what's configured)
echo "1. Checking IAM Policy Configuration:"
echo "--------------------------------------------"
echo "Job-level IAM (run.invoker):"
gcloud run jobs get-iam-policy "$JOB_NAME" \
  --region="$REGION" \
  --project="$PROJECT" \
  --format="table(bindings.members,bindings.role)" | grep -E "(run.invoker|$COMPUTE_SA)" || echo "⚠️  Not found"
echo ""

echo "Project-level IAM (serviceAccountTokenCreator):"
gcloud projects get-iam-policy "$PROJECT" \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:$COMPUTE_SA AND bindings.role:roles/iam.serviceAccountTokenCreator" \
  --format="table(bindings.role)" || echo "⚠️  Not found"
echo ""

# Method 2: Test if permissions are actually working
echo "2. Testing Permission Propagation:"
echo "--------------------------------------------"
echo "Attempting to test OIDC token generation..."
echo ""

# Try to manually trigger scheduler and check if it works
echo "Manually triggering scheduler to test if permissions have propagated..."
TRIGGER_RESULT=$(gcloud scheduler jobs run "$SCHEDULER_NAME" \
  --location="$REGION" \
  --project="$PROJECT" 2>&1)

if [ $? -eq 0 ]; then
  echo "✅ Scheduler trigger command succeeded"
else
  echo "❌ Scheduler trigger command failed"
  echo "$TRIGGER_RESULT"
fi
echo ""

# Wait a moment and check for execution
echo "Waiting 10 seconds for execution to be created..."
sleep 10

echo "Checking for new execution:"
EXECUTIONS=$(gcloud run jobs executions list \
  --job="$JOB_NAME" \
  --region="$REGION" \
  --project="$PROJECT" \
  --limit=1 \
  --format="value(metadata.name,status.startTime)" 2>&1)

if [ -n "$EXECUTIONS" ]; then
  echo "✅ Execution found - permissions may have propagated!"
  echo "$EXECUTIONS"
else
  echo "❌ No execution found - permissions may not have propagated yet"
fi
echo ""

# Method 3: Check scheduler logs for latest attempt
echo "3. Checking Latest Scheduler Attempt:"
echo "--------------------------------------------"
LATEST_LOG=$(gcloud logging read \
  "resource.type=cloud_scheduler_job AND resource.labels.job_id=$SCHEDULER_NAME" \
  --limit=1 \
  --project="$PROJECT" \
  --format=json 2>/dev/null | python3 -c "
import sys, json
try:
    log = json.load(sys.stdin)[0]
    payload = log.get('jsonPayload', {})
    status = payload.get('status', 'N/A')
    timestamp = log.get('timestamp', 'N/A')
    debug = payload.get('debugInfo', 'N/A')
    print(f'Status: {status}')
    print(f'Time: {timestamp}')
    print(f'Debug: {debug}')
    if status == 'UNAUTHENTICATED':
        print('❌ Still showing UNAUTHENTICATED - IAM may not have propagated')
    elif status == 'SUCCESS' or 'SUCCEEDED' in str(status):
        print('✅ Status shows success - IAM may have propagated!')
    else:
        print('⚠️  Status unclear - check manually')
except:
    print('Could not parse logs')
" 2>/dev/null)

if [ -n "$LATEST_LOG" ]; then
  echo "$LATEST_LOG"
else
  echo "Could not retrieve logs"
fi
echo ""

# Method 4: Check when permissions were last updated
echo "4. Permission Update Timestamps:"
echo "--------------------------------------------"
echo "Checking when IAM policies were last modified..."
echo ""
echo "Note: IAM propagation typically takes 1-5 minutes, but can take up to 10 minutes"
echo "in rare cases. If permissions were granted recently, wait a bit longer."
echo ""

# Calculate time since script was run (approximate)
echo "If you ran fix_oidc.sh recently, wait at least 5 minutes before testing again."
echo ""

echo "=========================================="
echo "Summary:"
echo "- IAM policies show what's configured (may not be propagated yet)"
echo "- Testing scheduler trigger shows if permissions actually work"
echo "- Scheduler logs show the actual authentication result"
echo "- If still UNAUTHENTICATED after 10 minutes, try additional permissions"
echo "=========================================="
