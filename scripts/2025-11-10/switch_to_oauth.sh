#!/bin/bash
# Switch Cloud Scheduler from OIDC to OAuth token authentication for Cloud Run Job

set -e

PROJECT="pax-nyc"
REGION="us-central1"
JOB_NAME="pax-collector"
SCHEDULER_NAME="pax-collector-schedule"

echo "=========================================="
echo "Switching to OAuth Token Authentication"
echo "=========================================="
echo ""
echo "Cloud Run Jobs require OAuth tokens, not OIDC!"
echo ""

PROJECT_NUMBER=$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "Step 1: Verify service account has run.invoker permission"
echo "--------------------------------------------"
gcloud run jobs get-iam-policy "$JOB_NAME" \
  --region="$REGION" \
  --project="$PROJECT" \
  --format="table(bindings.members,bindings.role)" | grep -E "(run.invoker|$COMPUTE_SA)" || echo "⚠️  Permission may be missing"

echo ""
echo "Step 2: Update Cloud Scheduler to use OAuth token"
echo "--------------------------------------------"
JOB_URI="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT}/jobs/${JOB_NAME}:run"

echo "Updating scheduler to use OAuth token instead of OIDC..."
gcloud scheduler jobs update http "$SCHEDULER_NAME" \
  --location="$REGION" \
  --project="$PROJECT" \
  --uri="$JOB_URI" \
  --http-method=POST \
  --oauth-service-account-email="$COMPUTE_SA" \
  --oauth-token-scope="https://www.googleapis.com/auth/cloud-platform" \
  --time-zone="UTC"

echo ""
echo "Step 3: Verify configuration"
echo "--------------------------------------------"
gcloud scheduler jobs describe "$SCHEDULER_NAME" \
  --location="$REGION" \
  --project="$PROJECT" \
  --format="value(httpTarget.oauthToken.serviceAccountEmail,httpTarget.oauthToken.scope)"

echo ""
echo "=========================================="
echo "OAuth configuration complete!"
echo "=========================================="
echo ""
echo "Step 4: Test scheduler"
echo "--------------------------------------------"
gcloud scheduler jobs run "$SCHEDULER_NAME" \
  --location="$REGION" \
  --project="$PROJECT"

echo ""
echo "Waiting 30 seconds for execution..."
sleep 30

echo ""
echo "Checking for execution:"
gcloud run jobs executions list \
  --job="$JOB_NAME" \
  --region="$REGION" \
  --project="$PROJECT" \
  --limit=1 \
  --format="table(metadata.name,status.startTime,status.succeededCount,status.failedCount)"
