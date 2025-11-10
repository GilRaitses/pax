#!/usr/bin/env bash
set -euo pipefail

PROJECT="${1:-pax-nyc}"

echo "=========================================="
echo "Checking Billing and Quotas for: $PROJECT"
echo "=========================================="
echo ""

# Check billing account
echo "Billing Account:"
gcloud billing projects describe "$PROJECT" --format="value(billingAccountName)" 2>&1 || echo "  ⚠️  No billing account linked"
echo ""

# Check Cloud Run quotas
echo "Cloud Run Quotas:"
gcloud compute project-info describe --project "$PROJECT" --format="table(quotas.metric,quotas.limit,quotas.usage)" 2>&1 | grep -i "run" || echo "  (No specific Cloud Run quotas found)"
echo ""

# Check GCS bucket
echo "GCS Bucket (pax-nyc-images):"
gcloud storage buckets describe gs://pax-nyc-images --project "$PROJECT" --format="table(location,storageClass,lifecycle)" 2>&1 || echo "  ⚠️  Bucket not found or not accessible"
echo ""

# Check current bucket size
echo "Current Bucket Size:"
gsutil du -sh gs://pax-nyc-images 2>&1 || echo "  (Unable to check size)"
echo ""

# Calculate requirements
echo "=========================================="
echo "Storage Requirements (2 weeks)"
echo "=========================================="
CAMERAS=82
IMAGES_PER_DAY=48
DAYS=14
TOTAL_IMAGES=$((CAMERAS * IMAGES_PER_DAY * DAYS))
IMAGE_SIZE_MB=0.1
TOTAL_STORAGE_GB=$(echo "scale=2; $TOTAL_IMAGES * $IMAGE_SIZE_MB / 1024" | bc)
DAILY_STORAGE_GB=$(echo "scale=2; $CAMERAS * $IMAGES_PER_DAY * $IMAGE_SIZE_MB / 1024" | bc)

echo "Cameras: $CAMERAS"
echo "Images per camera per day: $IMAGES_PER_DAY"
echo "Days: $DAYS"
echo "Total images: $TOTAL_IMAGES"
echo "Total storage needed: ${TOTAL_STORAGE_GB} GB"
echo "Daily storage: ${DAILY_STORAGE_GB} GB"
echo ""

# Check if billing is enabled
BILLING_ENABLED=$(gcloud billing projects describe "$PROJECT" --format="value(billingEnabled)" 2>&1 || echo "false")
if [[ "$BILLING_ENABLED" != "true" ]]; then
  echo "⚠️  WARNING: Billing may not be enabled!"
  echo "   This could block storage and compute operations"
else
  echo "✅ Billing is enabled"
fi
echo ""

