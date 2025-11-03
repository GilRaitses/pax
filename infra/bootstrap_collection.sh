#!/usr/bin/env bash
#
# Quick-start script to bootstrap local installs, run an initial collection,
# and deploy the scheduled Cloud Run job.
#
# Required environment variables:
#   PAX_PROJECT                GCP project ID (e.g., pax-nyc)
#   PAX_REGION                 Cloud Run / Scheduler region (e.g., us-central1)
#   PAX_BUCKET                 GCS bucket for uploads
#   GOOGLE_APPLICATION_CREDENTIALS  Path to service-account JSON
#
# Optional environment variables:
#   PAX_REMOTE_PREFIX          Object prefix inside the bucket (default: images)
#   PAX_BOOTSTRAP_MAX_CAMERAS  Number of cameras for the initial run (default: 5)
#   PAX_SERVICE_ACCOUNT        Service account email for Cloud Run job
#   PAX_SCHEDULE               Cron expression for Cloud Scheduler
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

required=(PAX_PROJECT PAX_REGION PAX_BUCKET GOOGLE_APPLICATION_CREDENTIALS)
for var in "${required[@]}"; do
  if [[ -z ${!var:-} ]]; then
    echo "Missing required environment variable: $var" >&2
    exit 1
  fi
done

PREFIX=${PAX_REMOTE_PREFIX:-images}
MAX_CAMERAS=${PAX_BOOTSTRAP_MAX_CAMERAS:-5}
SERVICE_ACCOUNT=${PAX_SERVICE_ACCOUNT:-pax-collector@${PAX_PROJECT}.iam.gserviceaccount.com}
SCHEDULE=${PAX_SCHEDULE:-"*/30 * * * *"}

echo "==> Installing Pax in editable mode"
python3 -m pip install --quiet --upgrade pip
python3 -m pip install --quiet -e .

if [[ ! -f .env ]]; then
  echo "==> Writing .env (existing file will be preserved)"
  cat <<EOF > .env
PAX_REMOTE_PROVIDER=gcs
PAX_REMOTE_BUCKET=${PAX_BUCKET}
PAX_REMOTE_PREFIX=${PREFIX}
GOOGLE_APPLICATION_CREDENTIALS=${GOOGLE_APPLICATION_CREDENTIALS}
EOF
else
  echo "==> .env already present; skipping"
fi

echo "==> Running initial data collection (max ${MAX_CAMERAS} cameras)"
python3 -m pax.scripts.collect \
  --max-cameras "$MAX_CAMERAS" \
  --gcs-bucket "$PAX_BUCKET" \
  --gcs-prefix "$PREFIX"

echo "==> Building warehouse parquet"
python3 -m pax.scripts.warehouse

echo "==> Deploying Cloud Run job and scheduler"
pushd infra/cloudrun > /dev/null
./deploy.sh \
  --project "$PAX_PROJECT" \
  --region "$PAX_REGION" \
  --bucket "$PAX_BUCKET" \
  --prefix "$PREFIX" \
  --service-account "$SERVICE_ACCOUNT" \
  --schedule "$SCHEDULE"
popd > /dev/null

echo "==> Triggering first Cloud Run execution"
gcloud run jobs execute pax-collector \
  --project "$PAX_PROJECT" \
  --region "$PAX_REGION"

echo "Bootstrap complete. Monitor executions with:"
echo "  gcloud run jobs executions list --project $PAX_PROJECT --region $PAX_REGION"

