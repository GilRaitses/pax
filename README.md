# Pax

Energetic pathfinding research toolkit for the CIS 667 term project. Pax houses the code for learning perception-aware heuristics over Manhattan street networks.

## Structure

- `src/pax`: Python package with data collection, feature engineering, and search components.
- `data`: Reserved for raw and intermediate datasets (not tracked).
- `notebooks`: Exploratory analysis and visualization (optional).
- `scripts`: Command-line utilities for ingest, training, and evaluation.

## Getting Started

1. Create and activate a Python 3.11+ environment.
2. Install the package in editable mode:

   ```bash
   pip install -e .
   ```

3. Configure environment variables in `.env` (see `src/pax/config.py` for expected keys).
4. Prime the storage directories (automatically created under `data/` on first run).
5. Trigger a collection sweep:

   ```bash
   # Discover cameras without downloading media
   python -m pax.scripts.collect --dry-run --max-cameras 5

   # Download JPEG frames and metadata for the first 5 cameras
   python -m pax.scripts.collect --max-cameras 5

   # Store only metadata (skip images)
   python -m pax.scripts.collect --max-cameras 5 --skip-images
   ```

   Snapshots are written to:

   - `data/raw/images/<camera_id>/<timestamp>.jpg`
   - `data/raw/metadata/<camera_id>/<timestamp>.json`
   - `data/raw/snapshots_<timestamp>.json` (batch manifest)

6. Build the parquet warehouse (one file per capture day):

   ```bash
   python -m pax.scripts.warehouse
   ```

   Parquet files are written to `data/warehouse/snapshots/`.

### Optional: Upload snapshots to Google Cloud Storage

1. Add the following to `.env` (do **not** commit this file):

   ```bash
   PAX_REMOTE_PROVIDER=gcs
   PAX_REMOTE_BUCKET=pax-nyc-images         # replace with your bucket name
   PAX_REMOTE_PREFIX=images                 # optional; defaults to "pax"
   GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account.json
   ```

2. Run the collector as usual. Uploaded files appear under `gs://<bucket>/<prefix>/<camera_id>/<timestamp>.jpg`.

   - Disable uploads explicitly: `python -m pax.scripts.collect --no-upload ...`
   - Override bucket/prefix per run: `python -m pax.scripts.collect --gcs-bucket my-bucket --gcs-prefix nightly`

### Optional: Deploy the collector to Cloud Run Jobs

The `infra/cloudrun/` directory contains a Dockerfile and helper script for deploying a recurring Cloud Run Job:

```bash
cd infra/cloudrun
./deploy.sh --project pax-nyc --region us-central1 \
    --bucket pax-nyc-images --prefix images
```

Deployment steps performed by the script:

- Builds `gcr.io/<project>/pax-collector` from the Pax source tree.
- Creates/updates a Cloud Run Job that executes `python -m pax.scripts.collect --skip-images`.
- Configures environment variables so the job streams artifacts into your GCS bucket.
- Sets up a Cloud Scheduler trigger that runs the job every 30 minutes.

Ensure the service account used by Cloud Run has `roles/storage.objectAdmin` on the bucket and that the project has a billing budget/lifecycle policy in place if you want automatic clean-up.

### One-command bootstrap

For a crash start (installs Pax, runs a first collection, builds the warehouse, deploys Cloud Run, and triggers the initial job) set the following environment variables and run:

```bash
export PAX_PROJECT=pax-nyc
export PAX_REGION=us-central1
export PAX_BUCKET=pax-nyc-images
export GOOGLE_APPLICATION_CREDENTIALS=$HOME/pax-ingest-key.json
export GOOGLE_API_KEY=your-google-api-key-here

./infra/bootstrap_collection.sh
```

Optional overrides:

- `PAX_REMOTE_PREFIX` — remote object prefix (default `images`)
- `PAX_BOOTSTRAP_MAX_CAMERAS` — number of cameras for the first run (default `5`)
- `PAX_SERVICE_ACCOUNT` — Cloud Run service account email (default `pax-collector@<project>.iam.gserviceaccount.com`)
- `PAX_SCHEDULE` — Cron expression for Cloud Scheduler (default every 30 minutes)

### Regenerate Figure 4 route preview

The route renderer uses Google Directions + Static Maps APIs together with the latest snapshot warehouse to color each path by stress:

```bash
python -m pax.scripts.render_routes --output-dir outputs/figures
# or simply
make figure4
```

Artifacts are saved under `outputs/figures/` (individual PNGs plus `figure4_routes.png`).

## Roadmap

- Implement NYC DOT Traffic Management API client with retry and caching.
- Harden feature encoding beyond the legacy 17-element vector (taxonomy + stats).
- Integrate computer vision feature extraction (violations, density, infrastructure).
- Build Ridge regression training pipeline and evaluation harness.
- Expose CLI tools for training, evaluation, and visualization.

