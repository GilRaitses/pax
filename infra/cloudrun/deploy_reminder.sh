#!/usr/bin/env bash
set -euo pipefail

# Deploy daily email reminder Cloud Function

PROJECT="${1:-pax-nyc}"
REGION="${2:-us-central1}"
EMAIL="${3:-gilraitses@gmail.com}"

FUNCTION_NAME="pax-daily-reminder"
FUNCTION_REGION="us-central1"

echo "=========================================="
echo "Deploying Daily Email Reminder"
echo "=========================================="
echo "Project: $PROJECT"
echo "Region: $FUNCTION_REGION"
echo "Email: $EMAIL"
echo ""

# Create function source directory
TMP_DIR=$(mktemp -d)
trap "rm -rf $TMP_DIR" EXIT

cp infra/cloudrun/send_daily_reminder.py "$TMP_DIR/main.py"

cat > "$TMP_DIR/requirements.txt" <<EOF
google-cloud-storage>=2.16.0
requests>=2.31.0
EOF

echo "Deploying Cloud Function..."
gcloud functions deploy "$FUNCTION_NAME" \
  --project "$PROJECT" \
  --region "$FUNCTION_REGION" \
  --runtime python311 \
  --trigger-http \
  --entry-point main \
  --set-env-vars PAX_REMOTE_BUCKET=pax-nyc-images,REMINDER_EMAIL="$EMAIL" \
  --allow-unauthenticated \
  --source "$TMP_DIR" \
  --timeout 540s \
  --memory 256MB

# Get function URL
FUNCTION_URL=$(gcloud functions describe "$FUNCTION_NAME" \
  --project "$PROJECT" \
  --region "$FUNCTION_REGION" \
  --format="value(httpsTrigger.url)")

echo ""
echo "Function deployed: $FUNCTION_URL"

# Create scheduler for daily reminders (8 AM UTC = 3 AM EST)
echo ""
echo "Creating daily reminder scheduler..."
REMINDER_SCHEDULER="pax-daily-reminder-schedule"

gcloud scheduler jobs create http "$REMINDER_SCHEDULER" \
  --project "$PROJECT" \
  --location "$REGION" \
  --schedule "0 8 * * *" \
  --uri "$FUNCTION_URL" \
  --http-method GET \
  --time-zone "UTC" || \
gcloud scheduler jobs update http "$REMINDER_SCHEDULER" \
  --project "$PROJECT" \
  --location "$REGION" \
  --schedule "0 8 * * *" \
  --uri "$FUNCTION_URL" \
  --http-method GET \
  --time-zone "UTC"

echo ""
echo "✅ Daily reminder scheduler created!"
echo "   Schedule: 0 8 * * * (8 AM UTC / 3 AM EST daily)"
echo "   Email: $EMAIL"

