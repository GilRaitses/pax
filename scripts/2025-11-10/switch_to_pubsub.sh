#!/bin/bash
# Switch Cloud Scheduler from HTTP to Pub/Sub trigger for Cloud Run Job

set -e

PROJECT="pax-nyc"
REGION="us-central1"
JOB_NAME="pax-collector"
SCHEDULER_NAME="pax-collector-schedule"
TOPIC_NAME="pax-collector-trigger"

echo "=========================================="
echo "Switching to Pub/Sub Trigger"
echo "=========================================="
echo ""

echo "Step 1: Create Pub/Sub topic"
echo "--------------------------------------------"
gcloud pubsub topics create "$TOPIC_NAME" \
  --project="$PROJECT" || echo "Topic may already exist"

echo ""
echo "Step 2: Update Cloud Run Job to subscribe to Pub/Sub"
echo "--------------------------------------------"
echo "⚠️  Cloud Run Jobs don't directly subscribe to Pub/Sub"
echo "   We need to create a Cloud Run Service that:"
echo "   1. Subscribes to Pub/Sub topic"
echo "   2. Triggers the Cloud Run Job"
echo ""
echo "This requires creating a new Service. Continue? (y/n)"
read -p "" -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 1
fi

echo ""
echo "Step 3: Update Cloud Scheduler to publish to Pub/Sub"
echo "--------------------------------------------"
gcloud scheduler jobs update pubsub "$SCHEDULER_NAME" \
  --location="$REGION" \
  --project="$PROJECT" \
  --schedule="*/30 * * * *" \
  --topic="$TOPIC_NAME" \
  --message-body='{"job":"pax-collector"}' || \
gcloud scheduler jobs create pubsub "$SCHEDULER_NAME" \
  --location="$REGION" \
  --project="$PROJECT" \
  --schedule="*/30 * * * *" \
  --topic="$TOPIC_NAME" \
  --message-body='{"job":"pax-collector"}'

echo ""
echo "=========================================="
echo "Pub/Sub setup complete!"
echo "=========================================="
echo ""
echo "Next: Create Cloud Run Service that subscribes to topic"
echo "and triggers the Job. This is more complex but reliable."
