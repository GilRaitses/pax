# GCS Bucket Setup Guide

## Install Google Cloud SDK

If `gcloud` is not installed, install it first:

```bash
# macOS
brew install google-cloud-sdk

# Or download from: https://cloud.google.com/sdk/docs/install
```

## Authenticate

```bash
gcloud auth login
gcloud config set project pax-nyc
```

## Create Bucket and Infrastructure

Run the setup script:

```bash
chmod +x /Users/gilraitses/setup_pax_infrastructure.sh
/Users/gilraitses/setup_pax_infrastructure.sh
```

Or run manually:

```bash
# 1. Create bucket
gcloud storage buckets create gs://pax-nyc-images \
    --project=pax-nyc \
    --location=us-east1 \
    --default-storage-class=STANDARD

# 2. Set lifecycle rule (24-hour retention)
cat > /tmp/lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 1}
      }
    ]
  }
}
EOF

gcloud storage buckets update gs://pax-nyc-images \
    --lifecycle-file=/tmp/lifecycle.json \
    --project=pax-nyc

# 3. Verify bucket
gcloud storage buckets describe gs://pax-nyc-images --project=pax-nyc
```

## After Bucket Creation

Deploy the Cloud Run collector:

```bash
cd ~/pax

export PAX_PROJECT=pax-nyc
export PAX_REGION=us-east1
export PAX_BUCKET=pax-nyc-images
export GOOGLE_APPLICATION_CREDENTIALS=$HOME/pax-ingest-key.json

./infra/bootstrap_collection.sh
```

## Note: Dashboard Stats

**Important:** The dashboard statistics come from **local collection files** (`data/raw/metadata`), not from the GCS bucket. The bucket is for:

1. **Backup storage** - Uploads copies of collected images/metadata
2. **Cloud Run** - The automated collector job uploads to GCS
3. **Long-term storage** - If you want historical data beyond local disk

Your local collection shows **45 images** collected from **40 cameras**. To update the dashboard stats JSON file after new collections:

```bash
cd ~/pax
./update_stats.sh
```

This refreshes `stats.json` and commits it so GitHub Pages shows updated numbers.

