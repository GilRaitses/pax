#!/bin/bash
# Run baseline generation with newly downloaded images
#
# This script:
# 1. Extracts features from all downloaded images
# 2. Computes stress scores per camera zone
# 3. Generates updated baseline heatmap
# 4. Updates data completeness reports

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

# Activate venv if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "=========================================="
echo "BASELINE GENERATION WITH NEW DATA"
echo "=========================================="
echo "Date: $(date)"
echo "Image directory: data/raw/images"
echo "=========================================="
echo

# Count images
IMAGE_COUNT=$(find data/raw/images -name "*.jpg" -type f | wc -l | tr -d ' ')
echo "Total images available: $IMAGE_COUNT"
echo

# Step 1: Extract features from all images
echo "Step 1/4: Extracting features from images..."
echo "This may take a while (~$IMAGE_COUNT images)..."
echo

# Launch Cinnamoroll monitor
echo "Launching Cinnamoroll monitor..."
scripts/2025-11-11/open_cinnamoroll_monitor.sh \
    data/raw/images \
    data/features \
    /tmp/baseline_run.log \
    1.5 \
    "$(date +%Y%m%d)" || {
    echo "⚠️  Monitor launch failed, continuing without monitor"
}

echo "Waiting 2 seconds for monitor to start..."
sleep 2
echo

scripts/2025-11-10/run_with_venv.sh \
    scripts/extract_all_features.py \
    --input-dir data/raw/images \
    --output-dir data/features \
    --format json \
    2>&1 | tee /tmp/baseline_run.log || {
    echo "ERROR: Feature extraction failed"
    exit 1
}

echo "✅ Feature extraction complete"
echo

# Find the most recent features file
LATEST_FEATURES=$(ls -t data/features/features_*.json 2>/dev/null | head -1)
if [ -z "$LATEST_FEATURES" ]; then
    echo "ERROR: No features file found"
    exit 1
fi

echo "Using features file: $LATEST_FEATURES"
echo

# Step 2: Compute stress scores
echo "Step 2/4: Computing stress scores..."
echo

# Check if image manifest exists, if not skip it
IMAGE_MANIFEST=""
if [ -f "data/manifests/image_manifest.yaml" ]; then
    IMAGE_MANIFEST="--image-manifest data/manifests/image_manifest.yaml"
elif [ -f "data/manifests/image_manifest.json" ]; then
    IMAGE_MANIFEST="--image-manifest data/manifests/image_manifest.json"
fi

scripts/2025-11-10/run_with_venv.sh \
    scripts/2025-11-10/compute_stress_scores.py \
    --camera-manifest data/manifests/corridor_cameras_numbered.json \
    $IMAGE_MANIFEST \
    --base-image-dir data/raw/images \
    --use-extracted-features \
    --features-path "$LATEST_FEATURES" \
    --output data/stress_scores_updated.json \
    || {
    echo "ERROR: Stress score computation failed"
    exit 1
}

echo "✅ Stress scores computed"
echo

# Step 3: Generate baseline heatmap
echo "Step 3/4: Generating baseline heatmap..."
echo

scripts/2025-11-10/run_with_venv.sh \
    scripts/2025-11-10/generate_baseline_heatmap.py \
    --stress-scores data/stress_scores_updated.json \
    --output docs/figures/baseline_heatmap_updated.png \
    || {
    echo "ERROR: Heatmap generation failed"
    exit 1
}

echo "✅ Baseline heatmap generated"
echo

# Step 4: Update data completeness reports
echo "Step 4/4: Updating data completeness reports..."
echo

python3 scripts/2025-11-10/process_images_by_zone.py \
    --base-image-dir data/raw/images \
    --output docs/reports/zone_data_availability_updated.json \
    || {
    echo "ERROR: Data availability report failed"
    exit 1
}

python3 scripts/2025-11-10/identify_zones_sufficient_data.py \
    --base-image-dir data/raw/images \
    --output docs/reports/data_completeness_updated.json \
    || {
    echo "ERROR: Data completeness report failed"
    exit 1
}

echo "✅ Data completeness reports updated"
echo

echo "=========================================="
echo "✅ BASELINE GENERATION COMPLETE"
echo "=========================================="
echo
echo "Outputs:"
echo "  - Features: data/features/extracted_features.json"
echo "  - Stress scores: data/stress_scores_updated.json"
echo "  - Heatmap: docs/figures/baseline_heatmap_updated.png"
echo "  - Data availability: docs/reports/zone_data_availability_updated.json"
echo "  - Data completeness: docs/reports/data_completeness_updated.json"
echo

