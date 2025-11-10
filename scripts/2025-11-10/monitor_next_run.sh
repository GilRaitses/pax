#!/usr/bin/env bash
set -euo pipefail

# Monitor the next scheduled Cloud Run job execution
# Usage: ./monitor_next_run.sh [--project PROJECT] [--region REGION] [--job JOB_NAME]

PROJECT="${PAX_GCP_PROJECT:-pax-nyc}"
REGION="${PAX_GCP_REGION:-us-central1}"
JOB_NAME="${PAX_JOB_NAME:-pax-collector}"

while [[ $# -gt 0 ]]; do
  case $1 in
    --project)
      PROJECT="$2"
      shift 2
      ;;
    --region)
      REGION="$2"
      shift 2
      ;;
    --job)
      JOB_NAME="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

echo "=========================================="
echo "Monitoring Next Scheduled Run"
echo "=========================================="
echo "Project: $PROJECT"
echo "Region: $REGION"
echo "Job: $JOB_NAME"
echo ""

# Get current time
CURRENT_TIME=$(date +%s)
CURRENT_HOUR=$(date +%H)
CURRENT_MINUTE=$(date +%M)

# Calculate next run time (every 30 minutes at :00 and :30)
if [ "$CURRENT_MINUTE" -lt 30 ]; then
  NEXT_RUN_MINUTE=30
  NEXT_RUN_HOUR=$CURRENT_HOUR
else
  NEXT_RUN_MINUTE=0
  NEXT_RUN_HOUR=$((CURRENT_HOUR + 1))
fi

NEXT_RUN_STR="${NEXT_RUN_HOUR}:${NEXT_RUN_MINUTE}"
echo "Current time: $(date '+%H:%M')"
echo "Next scheduled run: ${NEXT_RUN_STR}"
echo ""

# Wait until next run time
if [ "$CURRENT_MINUTE" -lt 30 ]; then
  WAIT_SECONDS=$((30 - CURRENT_MINUTE)) 
  WAIT_MINUTES=0
else
  WAIT_SECONDS=$((60 - CURRENT_MINUTE))
  WAIT_MINUTES=0
fi

if [ "$WAIT_SECONDS" -gt 0 ]; then
  echo "Waiting ${WAIT_SECONDS} seconds until next run..."
  sleep "$WAIT_SECONDS"
fi

echo ""
echo "=========================================="
echo "Checking for new executions..."
echo "=========================================="

# Get the most recent execution
LATEST_EXEC=$(gcloud run jobs executions list \
  --project "$PROJECT" \
  --region "$REGION" \
  --job "$JOB_NAME" \
  --limit 1 \
  --format="value(name,status.conditions[0].type,status.conditions[0].status,status.startTime)" 2>/dev/null || echo "")

if [ -z "$LATEST_EXEC" ]; then
  echo "❌ No executions found"
  exit 1
fi

# Parse execution details
EXEC_NAME=$(echo "$LATEST_EXEC" | cut -d$'\t' -f1)
EXEC_STATUS=$(echo "$LATEST_EXEC" | cut -d$'\t' -f3)
EXEC_START=$(echo "$LATEST_EXEC" | cut -d$'\t' -f4)

echo "Latest execution: $EXEC_NAME"
echo "Status: $EXEC_STATUS"
echo "Start time: $EXEC_START"
echo ""

# Check if execution is recent (within last 5 minutes)
EXEC_TIMESTAMP=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${EXEC_START%.*}" "+%s" 2>/dev/null || date -d "$EXEC_START" "+%s" 2>/dev/null || echo "0")
CURRENT_TIMESTAMP=$(date +%s)
TIME_DIFF=$((CURRENT_TIMESTAMP - EXEC_TIMESTAMP))

if [ "$TIME_DIFF" -lt 300 ]; then
  echo "✅ Execution started ${TIME_DIFF} seconds ago (recent)"
else
  echo "⚠️  Execution started ${TIME_DIFF} seconds ago (may not be the scheduled run)"
fi

# Wait a bit for execution to complete, then check status
echo ""
echo "Waiting 30 seconds for execution to start..."
sleep 30

# Check execution status again
EXEC_DETAILS=$(gcloud run jobs executions describe "$EXEC_NAME" \
  --project "$PROJECT" \
  --region "$REGION" \
  --format="yaml(status.conditions)" 2>/dev/null || echo "")

if [ -z "$EXEC_DETAILS" ]; then
  echo "❌ Could not retrieve execution details"
  exit 1
fi

echo ""
echo "=========================================="
echo "Execution Status"
echo "=========================================="
echo "$EXEC_DETAILS"

# Check if execution completed successfully
if echo "$EXEC_DETAILS" | grep -q "status: True" && echo "$EXEC_DETAILS" | grep -q "type: Completed"; then
  echo ""
  echo "✅ Execution completed successfully!"
  
  # Check for images collected
  echo ""
  echo "Checking for new images in GCS..."
  LATEST_IMAGE=$(gsutil ls -l "gs://pax-nyc-images/images/" 2>/dev/null | head -2 | tail -1 || echo "")
  if [ -n "$LATEST_IMAGE" ]; then
    echo "✅ Found images in GCS"
    echo "$LATEST_IMAGE"
  else
    echo "⚠️  No images found (may still be uploading)"
  fi
else
  echo ""
  echo "⚠️  Execution may still be running or failed"
  echo "Check logs: gcloud run jobs executions logs read $EXEC_NAME --region $REGION --project $PROJECT"
fi

