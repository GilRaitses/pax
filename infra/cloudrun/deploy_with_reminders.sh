#!/usr/bin/env bash
set -euo pipefail

# Deploy collector and set up daily email reminders

usage() {
  cat <<'EOF'
Deploy collector v2 with daily email reminders.

Required flags:
  --project         GCP project ID
  --region          Cloud Run region (e.g., us-central1)
  --bucket          GCS bucket name
  --email           Email address for daily reminders

Optional flags:
  --prefix          GCS prefix (default: images)
  --schedule        Collection schedule (default: "*/30 * * * *")
  --reminder-time   Daily reminder time UTC (default: "0 8 * * *" = 8 AM UTC)

Example:
  ./deploy_with_reminders.sh \
    --project pax-nyc \
    --region us-central1 \
    --bucket pax-nyc-images \
    --email your-email@example.com
EOF
}

PROJECT=""
REGION=""
BUCKET=""
EMAIL=""
PREFIX="images"
SCHEDULE="*/30 * * * *"
REMINDER_TIME="0 8 * * *"  # 8 AM UTC = 3 AM EST / 4 AM EDT

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2;;
    --region) REGION="$2"; shift 2;;
    --bucket) BUCKET="$2"; shift 2;;
    --email) EMAIL="$2"; shift 2;;
    --prefix) PREFIX="$2"; shift 2;;
    --schedule) SCHEDULE="$2"; shift 2;;
    --reminder-time) REMINDER_TIME="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown flag: $1"; usage; exit 1;;
  esac
done

if [[ -z "$PROJECT" || -z "$REGION" || -z "$BUCKET" || -z "$EMAIL" ]]; then
  echo "--project, --region, --bucket, and --email are required"
  usage
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

echo "=========================================="
echo "Deploying Collector v2 with Reminders"
echo "=========================================="
echo ""

# Step 1: Deploy collector
echo "Step 1: Deploying collector..."
./infra/cloudrun/deploy_collector_v2.sh \
  --project "$PROJECT" \
  --region "$REGION" \
  --bucket "$BUCKET" \
  --prefix "$PREFIX" \
  --schedule "$SCHEDULE"

echo ""
echo "=========================================="
echo "Step 2: Deploying email reminder function"
echo "=========================================="

# Deploy Cloud Function for email reminders
FUNCTION_NAME="pax-daily-reminder"
FUNCTION_REGION="us-central1"  # Cloud Functions region

# Create function source
TMP_DIR=$(mktemp -d)
cp infra/cloudrun/send_daily_reminder.py "$TMP_DIR/main.py"

# Create requirements.txt for function
cat > "$TMP_DIR/requirements.txt" <<EOF
google-cloud-storage>=2.16.0
requests>=2.31.0
EOF

# Deploy function
echo "Deploying Cloud Function: $FUNCTION_NAME"
gcloud functions deploy "$FUNCTION_NAME" \
  --project "$PROJECT" \
  --region "$FUNCTION_REGION" \
  --runtime python311 \
  --trigger-http \
  --entry-point main \
  --set-env-vars PAX_REMOTE_BUCKET="$BUCKET",REMINDER_EMAIL="$EMAIL" \
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

# Step 3: Create scheduler for daily reminders
echo ""
echo "=========================================="
echo "Step 3: Creating daily reminder scheduler"
echo "=========================================="

REMINDER_SCHEDULER="pax-daily-reminder-schedule"

gcloud scheduler jobs create http "$REMINDER_SCHEDULER" \
  --project "$PROJECT" \
  --location "$REGION" \
  --schedule "$REMINDER_TIME" \
  --uri "$FUNCTION_URL" \
  --http-method GET \
  --time-zone "UTC" || \
gcloud scheduler jobs update http "$REMINDER_SCHEDULER" \
  --project "$PROJECT" \
  --location "$REGION" \
  --schedule "$REMINDER_TIME" \
  --uri "$FUNCTION_URL" \
  --http-method GET \
  --time-zone "UTC"

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "✅ Collector: pax-collector-v2"
echo "   Schedule: $SCHEDULE (every 30 min)"
echo ""
echo "✅ Daily Reminders: $REMINDER_SCHEDULER"
echo "   Schedule: $REMINDER_TIME (daily)"
echo "   Email: $EMAIL"
echo ""
echo "📦 To package images manually:"
echo "   python3 -m src.pax.scripts.package_daily_images --bucket $BUCKET --date YYYY-MM-DD"
echo ""
rm -rf "$TMP_DIR"

