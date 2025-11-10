# Cloud Run Deployment

This directory contains a minimal Cloud Run Job that executes the Pax collector on a fixed schedule and streams JPEG snapshots into Google Cloud Storage.

## Requirements

- Google Cloud project with billing enabled
- `gcloud` CLI configured with the target project
- Service account with `roles/run.admin`, `roles/storage.objectAdmin`, `roles/cloudscheduler.admin`, and `roles/pubsub.admin`

## Deploy

```bash
./deploy.sh \
  --project pax-nyc \
  --region us-central1 \
  --bucket pax-nyc-images \
  --prefix images
```

This script builds the container, deploys a Cloud Run Job, creates a Pub/Sub topic, and schedules the job every 30 minutes via Cloud Scheduler. The job runs `python -m pax.scripts.collect --skip-images` inside the container, using environment variables to determine the GCS bucket and prefix.

## Local testing

To run the same container locally:

```bash
docker build -t pax-collector ..
docker run --rm \
  -e PAX_REMOTE_PROVIDER=gcs \
  -e PAX_REMOTE_BUCKET=pax-nyc-images \
  -e GOOGLE_APPLICATION_CREDENTIALS=/creds/key.json \
  -v $HOME/pax-ingest-key.json:/creds/key.json:ro \
  pax-collector
```

## Environment variables

- `PAX_REMOTE_PROVIDER` (default: `none`)
- `PAX_REMOTE_BUCKET`
- `PAX_REMOTE_PREFIX` (default: `pax`)
- `PAX_COLLECTOR_MAX_CAMERAS` (optional override for container runs)

