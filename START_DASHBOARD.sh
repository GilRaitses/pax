#!/usr/bin/env bash
# Start the Pax dashboard server

cd "$(dirname "$0")"
source venv/bin/activate

echo "Starting Pax Dashboard Server..."
echo ""
echo "Dashboard will be available at: http://localhost:8000"
echo "Press Ctrl+C to stop"
echo ""

python -m pax.scripts.stats_api

