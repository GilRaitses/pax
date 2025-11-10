#!/usr/bin/env bash
set -euo pipefail

# Use collect_manifest to only collect from cameras in cameras.yaml (40 corridor cameras)
# DOWNLOAD IMAGES - removed --skip-images flag
exec python -m pax.scripts.collect_manifest

