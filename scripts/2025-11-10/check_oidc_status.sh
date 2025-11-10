#!/bin/bash

PROJECT="pax-nyc"
REGION="us-central1"
JOB_NAME="pax-collector"
SCHEDULER_NAME="pax-collector-schedule"

echo "=========================================="
echo "OIDC Configuration Status Check"
echo "=========================================="
echo ""

# Get compute service account
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
echo "Compute Service Account: $COMPUTE_SA"
echo ""

echo "1. Checking IAM permissions on Cloud Run job:"
echo "--------------------------------------------"
gcloud run jobs get-iam-policy "$JOB_NAME" \
  --region="$REGION" \
  --project="$PROJECT" \
  --format="table(bindings.members,bindings.role)" | grep -E "(run.invoker|$COMPUTE_SA)" || echo "⚠️  run.invoker permission not found for $COMPUTE_SA"
echo ""

echo "2. Checking project-level IAM permissions:"
echo "--------------------------------------------"
gcloud projects get-iam-policy "$PROJECT" \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:$COMPUTE_SA" \
  --format="table(bindings.role)" | grep -E "(serviceAccountTokenCreator|run.admin|serviceAccountUser)" || echo "⚠️  No relevant project-level permissions found"
echo ""

echo "3. Checking scheduler OIDC configuration:"
echo "--------------------------------------------"
SCHEDULER_CONFIG=$(gcloud scheduler jobs describe "$SCHEDULER_NAME" \
  --location="$REGION" \
  --project="$PROJECT" \
  --format=json)

echo "OIDC Service Account:"
echo "$SCHEDULER_CONFIG" | jq -r '.httpTarget.oidcToken.serviceAccountEmail'
echo ""
echo "OIDC Audience:"
echo "$SCHEDULER_CONFIG" | jq -r '.httpTarget.oidcToken.audience'
echo ""
echo "Expected Audience:"
JOB_URI="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT}/jobs/${JOB_NAME}:run"
echo "$JOB_URI"
echo ""

if echo "$SCHEDULER_CONFIG" | jq -r '.httpTarget.oidcToken.serviceAccountEmail' | grep -q "$COMPUTE_SA"; then
  echo "✅ OIDC Service Account matches compute service account"
else
  echo "❌ OIDC Service Account does NOT match compute service account"
fi

if echo "$SCHEDULER_CONFIG" | jq -r '.httpTarget.oidcToken.audience' | grep -q "$JOB_URI"; then
  echo "✅ OIDC Audience matches job URI"
else
  echo "❌ OIDC Audience does NOT match job URI"
fi
echo ""

echo "4. Recent scheduler execution status:"
echo "--------------------------------------------"
gcloud logging read \
  "resource.type=cloud_scheduler_job AND resource.labels.job_id=$SCHEDULER_NAME" \
  --limit=3 \
  --project="$PROJECT" \
  --format="table(timestamp,jsonPayload.status,jsonPayload.debugInfo)" | head -5
echo ""

echo "=========================================="
echo "Status check complete!"
