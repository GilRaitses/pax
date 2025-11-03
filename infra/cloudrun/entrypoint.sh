#!/usr/bin/env bash
set -euo pipefail

# Use collect_manifest to only collect from cameras in cameras.yaml (40 corridor cameras)
exec python -m pax.scripts.collect_manifest --skip-images

