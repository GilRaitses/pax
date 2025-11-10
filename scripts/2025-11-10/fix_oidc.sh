#!/bin/bash
set -e

PROJECT="pax-nyc"
REGION="us-central1"
JOB_NAME="pax-collector"
SCHEDULER_NAME="pax-collector-schedule"

echo "=========================================="
echo "OIDC Authentication Fix Script"
echo "=========================================="
echo ""

echo "Step 1: Get compute service account"
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
echo "Compute Service Account: $COMPUTE_SA"
echo ""

echo "Step 2: Grant run.invoker permission to Cloud Run job"
gcloud run jobs add-iam-policy-binding "$JOB_NAME" \
  --region="$REGION" \
  --project="$PROJECT" \
  --member="serviceAccount:$COMPUTE_SA" \
  --role="roles/run.invoker" \
  --quiet || echo "Permission may already exist, continuing..."
echo ""

echo "Step 3: Grant serviceAccountTokenCreator permission"
echo "This allows the service account to create OIDC tokens"
gcloud projects add-iam-policy-binding "$PROJECT" \
  --member="serviceAccount:$COMPUTE_SA" \
  --role="roles/iam.serviceAccountTokenCreator" \
  --quiet || echo "Permission may already exist, continuing..."
echo ""

echo "Step 4: Verify and update scheduler OIDC configuration"
JOB_URI="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT}/jobs/${JOB_NAME}:run"
echo "Job URI: $JOB_URI"
echo "OIDC Service Account: $COMPUTE_SA"
echo ""

gcloud scheduler jobs update http "$SCHEDULER_NAME" \
  --location="$REGION" \
  --project="$PROJECT" \
  --oidc-service-account-email="$COMPUTE_SA" \
  --oidc-token-audience="$JOB_URI" \
  --quiet
echo ""

echo "Step 5: Wait 60 seconds for IAM propagation"
echo "IAM changes can take up to 5 minutes to propagate..."
for i in {60..1}; do
  echo -ne "Waiting: $i seconds\r"
  sleep 1
done
echo ""
echo ""

echo "Step 6: Test scheduler manually"
gcloud scheduler jobs run "$SCHEDULER_NAME" \
  --location="$REGION" \
  --project="$PROJECT"
echo ""

echo "Step 7: Wait 30 seconds for execution to be created..."
sleep 30
echo ""

echo "Step 8: Check for execution"
echo "=========================================="
gcloud run jobs executions list \
  --job="$JOB_NAME" \
  --region="$REGION" \
  --project="$PROJECT" \
  --limit=3 \
  --format="table(metadata.name,status.startTime,status.succeededCount,status.failedCount)"
echo ""

echo "=========================================="
echo "Fix script complete!"
echo ""
echo "If you see a new execution above, the fix worked! ✅"
echo "If no execution appears, check the scheduler logs for errors."
echo ""
echo "Check scheduler logs:"
echo "  gcloud logging read \"resource.type=cloud_scheduler_job AND resource.labels.job_id=$SCHEDULER_NAME\" --limit=5 --project=$PROJECT"
