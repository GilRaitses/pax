#!/bin/bash
# Quick script to delete the old job in us-east1

echo "Deleting old pax-collector job in us-east1..."
gcloud run jobs delete pax-collector \
  --region=us-east1 \
  --project=pax-nyc \
  --quiet

echo "Deleting old scheduler in us-east1..."
gcloud scheduler jobs delete pax-collector-schedule \
  --location=us-east1 \
  --project=pax-nyc \
  --quiet

echo ""
echo "✅ Cleanup complete!"
echo "Remaining:"
echo "  - Job: pax-collector in us-central1"
echo "  - Scheduler: pax-collector-schedule in us-central1"
