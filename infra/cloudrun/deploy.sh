#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Deploy the Pax collector as a Cloud Run Job and schedule it every 30 minutes.

Required flags:
  --project         GCP project ID
  --region          Cloud Run region (e.g., us-central1)
  --bucket          GCS bucket that will receive uploads

Optional flags:
  --prefix          GCS object prefix (default: images)
  --service-account Service account email with storage.objectAdmin (default: pax-collector@<project>.iam.gserviceaccount.com)
  --schedule        Cron expression for Cloud Scheduler (default: "*/30 * * * *")

Example:
  ./deploy.sh --project pax-nyc --region us-central1 --bucket pax-nyc-images
EOF
}

PROJECT=""
REGION=""
BUCKET=""
PREFIX="images"
SERVICE_ACCOUNT=""
SCHEDULE="*/30 * * * *"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2;;
    --region) REGION="$2"; shift 2;;
    --bucket) BUCKET="$2"; shift 2;;
    --prefix) PREFIX="$2"; shift 2;;
    --service-account) SERVICE_ACCOUNT="$2"; shift 2;;
    --schedule) SCHEDULE="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown flag: $1"; usage; exit 1;;
  esac
done

if [[ -z "$PROJECT" || -z "$REGION" || -z "$BUCKET" ]]; then
  echo "--project, --region, and --bucket are required"
  usage
  exit 1
fi

SERVICE_ACCOUNT=${SERVICE_ACCOUNT:-pax-collector@$PROJECT.iam.gserviceaccount.com}
IMAGE="gcr.io/$PROJECT/pax-collector"
JOB_NAME="pax-collector"
SCHEDULER_NAME="pax-collector-schedule"
TOPIC="projects/$PROJECT/topics/run-jobs-trigger"

echo "Building container image $IMAGE"
gcloud builds submit --project "$PROJECT" --tag "$IMAGE" ../..

echo "Ensuring Pub/Sub topic $TOPIC exists"
gcloud pubsub topics describe "$TOPIC" --project "$PROJECT" >/dev/null 2>&1 || \
  gcloud pubsub topics create "$TOPIC" --project "$PROJECT"

echo "Deploying Cloud Run job $JOB_NAME"
gcloud run jobs deploy "$JOB_NAME" \
  --project "$PROJECT" \
  --region "$REGION" \
  --image "$IMAGE" \
  --tasks 1 \
  --set-env-vars PAX_REMOTE_PROVIDER=gcs,PAX_REMOTE_BUCKET="$BUCKET",PAX_REMOTE_PREFIX="$PREFIX" \
  --service-account "$SERVICE_ACCOUNT"

echo "Creating Cloud Scheduler trigger $SCHEDULER_NAME"
gcloud scheduler jobs create pubsub "$SCHEDULER_NAME" \
  --project "$PROJECT" \
  --location "$REGION" \
  --schedule "$SCHEDULE" \
  --topic "$TOPIC" \
  --message-body "{\"jobName\":\"$JOB_NAME\"}" \
  --time-zone "UTC" || \
gcloud scheduler jobs update pubsub "$SCHEDULER_NAME" \
  --project "$PROJECT" \
  --location "$REGION" \
  --schedule "$SCHEDULE" \
  --topic "$TOPIC" \
  --message-body "{\"jobName\":\"$JOB_NAME\"}" \
  --time-zone "UTC"

echo "Deployment complete. Run the job manually with:"
echo "  gcloud run jobs execute $JOB_NAME --region $REGION --project $PROJECT"

