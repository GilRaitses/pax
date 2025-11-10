#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Deploy the Pax collector v2 as a Cloud Run Job with numbered camera manifest.

This script:
1. Cancels existing jobs and schedulers
2. Generates numbered camera manifest matching partitioning map
3. Deploys new Cloud Run Job
4. Sets up Cloud Scheduler to trigger job directly (not via Pub/Sub)

Required flags:
  --project         GCP project ID
  --region          Cloud Run region (e.g., us-central1)
  --bucket          GCS bucket that will receive uploads

Optional flags:
  --prefix          GCS object prefix (default: images)
  --service-account Service account email (default: pax-collector@<project>.iam.gserviceaccount.com)
  --schedule        Cron expression for Cloud Scheduler (default: "*/30 * * * *")
  --manifest        Path to camera manifest (default: data/manifests/corridor_cameras_numbered.json)

Example:
  ./deploy_collector.sh --project pax-nyc --region us-central1 --bucket pax-nyc-images
EOF
}

PROJECT=""
REGION=""
BUCKET=""
PREFIX="images"
SERVICE_ACCOUNT=""
SCHEDULE="*/30 * * * *"
MANIFEST="data/manifests/corridor_cameras_numbered.json"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2;;
    --region) REGION="$2"; shift 2;;
    --bucket) BUCKET="$2"; shift 2;;
    --prefix) PREFIX="$2"; shift 2;;
    --service-account) SERVICE_ACCOUNT="$2"; shift 2;;
    --schedule) SCHEDULE="$2"; shift 2;;
    --manifest) MANIFEST="$2"; shift 2;;
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
OLD_JOB_NAME="pax-collector-v2"
OLD_SCHEDULER_NAME="pax-collector-v2-schedule"

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

echo "=========================================="
echo "Step 1: Generate numbered camera manifest"
echo "=========================================="
python3 -m src.pax.scripts.generate_numbered_camera_manifest \
  --output "$MANIFEST" \
  --log-level INFO

if [[ ! -f "$MANIFEST" ]]; then
  echo "ERROR: Failed to generate manifest at $MANIFEST"
  exit 1
fi

echo ""
echo "Manifest generated: $MANIFEST"
echo "Cameras in manifest: $(python3 -c "import json; print(len(json.load(open('$MANIFEST'))['cameras']))")"

echo ""
echo "=========================================="
echo "Step 2: Cancel existing jobs and schedulers"
echo "=========================================="

# Delete old scheduler if exists
if gcloud scheduler jobs describe "$OLD_SCHEDULER_NAME" --project "$PROJECT" --location "$REGION" &>/dev/null; then
  echo "Deleting old scheduler: $OLD_SCHEDULER_NAME"
  gcloud scheduler jobs delete "$OLD_SCHEDULER_NAME" \
    --project "$PROJECT" \
    --location "$REGION" \
    --quiet || true
else
  echo "Old scheduler not found: $OLD_SCHEDULER_NAME"
fi

# Delete old job if exists
if gcloud run jobs describe "$OLD_JOB_NAME" --project "$PROJECT" --region "$REGION" &>/dev/null; then
  echo "Deleting old job: $OLD_JOB_NAME"
  gcloud run jobs delete "$OLD_JOB_NAME" \
    --project "$PROJECT" \
    --region "$REGION" \
    --quiet || true
else
  echo "Old job not found: $OLD_JOB_NAME"
fi

# Delete Pub/Sub topic if exists (no longer needed)
if gcloud pubsub topics describe "run-jobs-trigger" --project "$PROJECT" &>/dev/null; then
  echo "Deleting Pub/Sub topic: run-jobs-trigger"
  gcloud pubsub topics delete "run-jobs-trigger" --project "$PROJECT" --quiet || true
fi

echo ""
echo "=========================================="
echo "Step 3: Build container image"
echo "=========================================="
# Ensure manifest exists before building
if [[ ! -f "$MANIFEST" ]]; then
  echo "ERROR: Manifest not found: $MANIFEST"
  echo "Please run the manifest generation step first"
  exit 1
fi

# Create Dockerfile in repo (will be included in build context)
cat > infra/cloudrun/Dockerfile <<'DOCKERFILE'
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy project files and install package
COPY pyproject.toml README.md /app/
COPY src /app/src
RUN pip install --upgrade pip && pip install .

# Copy numbered camera manifest
COPY data/manifests/corridor_cameras_numbered.json /app/data/manifests/corridor_cameras_numbered.json

# Copy entrypoint
COPY infra/cloudrun/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
DOCKERFILE

cat > /tmp/cloudbuild.yaml <<EOF
steps:
- name: 'gcr.io/cloud-builders/docker'
  args: ['build', '-f', 'infra/cloudrun/Dockerfile', '-t', '$IMAGE', '.']
images:
- '$IMAGE'
EOF

echo "Build context size: $(du -sh . | cut -f1) (with .gcloudignore)"
gcloud builds submit --project "$PROJECT" --config /tmp/cloudbuild.yaml .
rm -f /tmp/cloudbuild.yaml

echo ""
echo "=========================================="
echo "Step 4: Deploy Cloud Run Job"
echo "=========================================="
gcloud run jobs deploy "$JOB_NAME" \
  --project "$PROJECT" \
  --region "$REGION" \
  --image "$IMAGE" \
  --tasks 1 \
  --set-env-vars PAX_REMOTE_PROVIDER=gcs,PAX_REMOTE_BUCKET="$BUCKET",PAX_REMOTE_PREFIX="$PREFIX",PAX_CAMERA_MANIFEST="/app/data/manifests/corridor_cameras_numbered.json" \
  --service-account "$SERVICE_ACCOUNT" \
  --memory 512Mi \
  --cpu 1 \
  --max-retries 3 \
  --task-timeout 10m

echo ""
echo "=========================================="
echo "Step 5: Grant run.invoker permission to service accounts"
echo "=========================================="
# Grant permission for job's service account to invoke the job
gcloud run jobs add-iam-policy-binding "$JOB_NAME" \
  --project "$PROJECT" \
  --region "$REGION" \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/run.invoker" \
  --quiet || echo "Permission may already exist, continuing..."

# Grant permission for Cloud Scheduler's compute service account to invoke the job
# Cloud Scheduler uses the project's compute service account for OIDC authentication
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')
COMPUTE_SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "Granting run.invoker permission to Cloud Scheduler's service account: $COMPUTE_SERVICE_ACCOUNT"
gcloud run jobs add-iam-policy-binding "$JOB_NAME" \
  --project "$PROJECT" \
  --region "$REGION" \
  --member="serviceAccount:${COMPUTE_SERVICE_ACCOUNT}" \
  --role="roles/run.invoker" \
  --quiet || echo "Permission may already exist, continuing..."

echo ""
echo "=========================================="
echo "Step 6: Create Cloud Scheduler (direct HTTP trigger)"
echo "=========================================="

# Get the job URI for direct HTTP trigger
JOB_URI="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT}/jobs/${JOB_NAME}:run"

# Cloud Scheduler must use the compute service account for OIDC authentication
# to invoke Cloud Run jobs via HTTP
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')
SCHEDULER_SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# Create scheduler that triggers job directly via HTTP
gcloud scheduler jobs create http "$SCHEDULER_NAME" \
  --project "$PROJECT" \
  --location "$REGION" \
  --schedule "$SCHEDULE" \
  --uri "$JOB_URI" \
  --http-method POST \
  --oidc-service-account-email "$SCHEDULER_SERVICE_ACCOUNT" \
  --oidc-token-audience "$JOB_URI" \
  --time-zone "UTC" || \
gcloud scheduler jobs update http "$SCHEDULER_NAME" \
  --project "$PROJECT" \
  --location "$REGION" \
  --schedule "$SCHEDULE" \
  --uri "$JOB_URI" \
  --http-method POST \
  --oidc-service-account-email "$SCHEDULER_SERVICE_ACCOUNT" \
  --oidc-token-audience "$JOB_URI" \
  --time-zone "UTC"

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Job: $JOB_NAME"
echo "Scheduler: $SCHEDULER_NAME"
echo "Schedule: $SCHEDULE"
echo "Manifest: $MANIFEST"
echo ""
echo "Test the job manually:"
echo "  gcloud run jobs execute $JOB_NAME --region $REGION --project $PROJECT"
echo ""
echo "Check job status:"
echo "  gcloud run jobs describe $JOB_NAME --region $REGION --project $PROJECT"
echo ""

