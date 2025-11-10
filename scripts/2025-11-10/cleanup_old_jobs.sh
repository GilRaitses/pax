#!/bin/bash
set -e

PROJECT="pax-nyc"
ACTIVE_REGION="us-central1"
ACTIVE_JOB="pax-collector"
ACTIVE_SCHEDULER="pax-collector-schedule"

echo "=========================================="
echo "Cleaning Up Old Cloud Run Jobs and Schedulers"
echo "=========================================="
echo ""

echo "This script will:"
echo "1. Keep: $ACTIVE_JOB in $ACTIVE_REGION"
echo "2. Delete: All other Cloud Run jobs"
echo "3. Keep: $ACTIVE_SCHEDULER in $ACTIVE_REGION"
echo "4. Delete: All other schedulers"
echo ""

read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 1
fi

echo ""
echo "Step 1: Listing all Cloud Run jobs..."
echo "--------------------------------------------"
gcloud run jobs list --project="$PROJECT" --format="table(name,region)"

echo ""
echo "Step 2: Deleting old Cloud Run jobs..."
echo "--------------------------------------------"

# Get all jobs
JOBS=$(gcloud run jobs list --project="$PROJECT" --format="value(name,region)" | awk '{print $1","$2}')

for job_info in $JOBS; do
    IFS=',' read -r job_name region <<< "$job_info"
    
    if [[ "$job_name" == "$ACTIVE_JOB" && "$region" == "$ACTIVE_REGION" ]]; then
        echo "✅ Keeping: $job_name in $region"
    else
        echo "🗑️  Deleting: $job_name in $region"
        gcloud run jobs delete "$job_name" \
            --region="$region" \
            --project="$PROJECT" \
            --quiet || echo "  (May not exist or already deleted)"
    fi
done

echo ""
echo "Step 3: Listing all Cloud Schedulers..."
echo "--------------------------------------------"
gcloud scheduler jobs list --project="$PROJECT" --format="table(name,location)"

echo ""
echo "Step 4: Deleting old schedulers..."
echo "--------------------------------------------"

# Get all schedulers
SCHEDULERS=$(gcloud scheduler jobs list --project="$PROJECT" --format="value(name)" | awk -F'/' '{print $(NF-1)","$NF}')

for scheduler_info in $SCHEDULERS; do
    IFS=',' read -r location scheduler_name <<< "$scheduler_info"
    
    if [[ "$scheduler_name" == "$ACTIVE_SCHEDULER" && "$location" == "$ACTIVE_REGION" ]]; then
        echo "✅ Keeping: $scheduler_name in $location"
    else
        echo "🗑️  Deleting: $scheduler_name in $location"
        gcloud scheduler jobs delete "$scheduler_name" \
            --location="$location" \
            --project="$PROJECT" \
            --quiet || echo "  (May not exist or already deleted)"
    fi
done

echo ""
echo "=========================================="
echo "Cleanup Complete!"
echo "=========================================="
echo ""
echo "Remaining resources:"
echo "  Job: $ACTIVE_JOB in $ACTIVE_REGION"
echo "  Scheduler: $ACTIVE_SCHEDULER in $ACTIVE_REGION"
echo ""

