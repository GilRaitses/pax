#!/usr/bin/env bash
# Setup Pax NYC GCS bucket and infrastructure

set -e

# Add gcloud to PATH (Homebrew install location)
export PATH="/opt/homebrew/share/google-cloud-sdk/bin:$PATH"
export CLOUDSDK_PYTHON=$(which python3)

PROJECT="pax-nyc"
BUCKET="pax-nyc-images"
REGION="us-east1"

echo "Setting up Pax NYC infrastructure..."
echo "Project: $PROJECT"
echo "Bucket: $BUCKET"
echo "Region: $REGION"
echo ""

# Check if bucket exists
echo "Checking for existing buckets..."
if gcloud storage buckets describe gs://$BUCKET --project=$PROJECT 2>/dev/null; then
    echo "Bucket gs://$BUCKET already exists"
else
    echo "Creating bucket gs://$BUCKET..."
    gcloud storage buckets create gs://$BUCKET \
        --project=$PROJECT \
        --location=$REGION \
        --default-storage-class=STANDARD
    echo "Bucket created successfully"
fi

# Set lifecycle rule (24-hour retention)
echo ""
echo "Setting lifecycle rule (24-hour retention)..."
cat > /tmp/pax-lifecycle.json <<EOF
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

gcloud storage buckets update gs://$BUCKET \
    --lifecycle-file=/tmp/pax-lifecycle.json \
    --project=$PROJECT

echo "Lifecycle rule set (files deleted after 1 day)"

# Verify bucket
echo ""
echo "Bucket details:"
gcloud storage buckets describe gs://$BUCKET --project=$PROJECT

echo ""
echo "Bucket setup complete!"
echo ""
echo "Next steps:"
echo "1. Deploy Cloud Run collector: cd ~/pax && ./infra/bootstrap_collection.sh"
echo "2. Or manually: cd ~/pax/infra/cloudrun && ./deploy.sh --project $PROJECT --region $REGION --bucket $BUCKET"
