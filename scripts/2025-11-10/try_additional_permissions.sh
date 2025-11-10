#!/bin/bash
# Try granting additional permissions that might be needed

PROJECT="pax-nyc"
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "Granting additional permissions that might be needed..."
echo ""

echo "1. Granting roles/iam.serviceAccountUser..."
gcloud projects add-iam-policy-binding "$PROJECT" \
  --member="serviceAccount:$COMPUTE_SA" \
  --role="roles/iam.serviceAccountUser" \
  --quiet || echo "May already exist"

echo "2. Granting roles/run.admin (broader Cloud Run permissions)..."
gcloud projects add-iam-policy-binding "$PROJECT" \
  --member="serviceAccount:$COMPUTE_SA" \
  --role="roles/run.admin" \
  --quiet || echo "May already exist"

echo ""
echo "Waiting 60 seconds for IAM propagation..."
sleep 60

echo ""
echo "Testing scheduler..."
gcloud scheduler jobs run pax-collector-schedule \
  --location=us-central1 \
  --project=pax-nyc

echo ""
echo "Waiting 30 seconds..."
sleep 30

echo ""
echo "Checking for execution:"
gcloud run jobs executions list \
  --job=pax-collector \
  --region=us-central1 \
  --project=pax-nyc \
  --limit=1
