# Cloud Run Deployment

This directory contains a minimal Cloud Run Job that executes the Pax collector on a fixed schedule and streams JPEG snapshots into Google Cloud Storage.

## Requirements

- Google Cloud project with billing enabled
- `gcloud` CLI configured with the target project
- Service account with `roles/run.admin`, `roles/storage.objectAdmin`, `roles/cloudscheduler.admin`, and `roles/pubsub.admin`

## Deploy

```bash
cd infra/cloudrun
./deploy_collector.sh \
  --project pax-nyc \
  --region us-central1 \
  --bucket pax-nyc-images
```

Or deploy everything (collector + email reminders):

```bash
cd infra/cloudrun
./deploy_with_reminders.sh \
  --project pax-nyc \
  --region us-central1 \
  --bucket pax-nyc-images \
  --email your-email@example.com
```

This script builds the container, deploys a Cloud Run Job, and schedules the job every 30 minutes via Cloud Scheduler. The job runs `python -m src.pax.scripts.collect_manifest` inside the container, using the numbered camera manifest (`data/manifests/corridor_cameras_numbered.json`) to collect from 82 cameras in the purple corridor.

## Local testing

To run the same container locally:

```bash
# From repo root
docker build -f infra/cloudrun/Dockerfile -t pax-collector .
docker run --rm \
  -e PAX_REMOTE_PROVIDER=gcs \
  -e PAX_REMOTE_BUCKET=pax-nyc-images \
  -e PAX_REMOTE_PREFIX=images \
  -e PAX_CAMERA_MANIFEST=/app/data/manifests/corridor_cameras_numbered.json \
  -e GOOGLE_APPLICATION_CREDENTIALS=/creds/key.json \
  -v $HOME/pax-ingest-key.json:/creds/key.json:ro \
  pax-collector
```

## Environment variables

- `PAX_REMOTE_PROVIDER` (default: `none`, set to `gcs` for Cloud Storage)
- `PAX_REMOTE_BUCKET` (required, e.g., `pax-nyc-images`)
- `PAX_REMOTE_PREFIX` (default: `images`)
- `PAX_CAMERA_MANIFEST` (default: `/app/data/manifests/corridor_cameras_numbered.json`)

## Scripts

- `deploy_collector.sh` - Deploy collector job and scheduler
- `deploy_reminder.sh` - Deploy email reminder Cloud Function
- `deploy_with_reminders.sh` - Deploy everything together
- `check_billing_quota.sh` - Check billing and quota status

