#!/usr/bin/env bash
set -euo pipefail

# Collect from numbered camera manifest matching partitioning map
# The manifest is passed via PAX_CAMERA_MANIFEST environment variable
# or defaults to /app/data/corridor_cameras_numbered.json

MANIFEST="${PAX_CAMERA_MANIFEST:-/app/data/corridor_cameras_numbered.json}"

if [[ ! -f "$MANIFEST" ]]; then
  echo "ERROR: Camera manifest not found: $MANIFEST"
  echo "Please ensure the manifest is available in the container"
  exit 1
fi

echo "Using camera manifest: $MANIFEST"
echo "Cameras in manifest: $(python3 -c "import json; print(len(json.load(open('$MANIFEST'))['cameras']))")"

# Use collect_manifest to collect from cameras in the numbered manifest
# This ensures cameras are collected in the same order as the partitioning map
exec python3 -m src.pax.scripts.collect_manifest --manifest "$MANIFEST"

