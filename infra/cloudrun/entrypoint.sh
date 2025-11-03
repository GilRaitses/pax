#!/usr/bin/env bash
set -euo pipefail

exec python -m pax.scripts.collect --skip-images --max-cameras "${PAX_COLLECTOR_MAX_CAMERAS:-108}"

