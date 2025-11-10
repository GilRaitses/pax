#!/bin/bash

PROJECT="pax-nyc"

echo "Opening Google Cloud Console links..."
echo ""

# Cloud Run Jobs
echo "1. Opening Cloud Run Jobs..."
open "https://console.cloud.google.com/run/jobs?project=$PROJECT"

sleep 2

# Cloud Scheduler
echo "2. Opening Cloud Scheduler..."
open "https://console.cloud.google.com/cloudscheduler?project=$PROJECT"

sleep 2

# IAM & Admin
echo "3. Opening IAM & Admin..."
open "https://console.cloud.google.com/iam-admin/iam?project=$PROJECT"

echo ""
echo "All console pages opened!"
echo ""
echo "Check these in order:"
echo "1. IAM & Admin → Search for compute service account → Verify roles"
echo "2. Cloud Run → pax-collector → Permissions → Verify run.invoker"
echo "3. Cloud Scheduler → pax-collector-schedule → Check OIDC config"
echo "4. Cloud Scheduler → Click RUN NOW → Check if execution appears"
