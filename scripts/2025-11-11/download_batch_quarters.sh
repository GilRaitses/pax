#!/bin/bash
# Download images in batches: quarters (6-hour periods)
#
# Sequence:
# 1. Yesterday's Q3 (noon-6pm)
# 2. Yesterday's Q4 (6pm-midnight)
# 3. Today's Q1 (midnight-6am)
# 4. Today's Q2 (6am-noon) - wait until after noon

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

# Get dates
YESTERDAY=$(date -v-1d +"%Y-%m-%d" 2>/dev/null || date -d "yesterday" +"%Y-%m-%d")
TODAY=$(date +"%Y-%m-%d")
NOW_HOUR=$(date +"%H")

echo "=========================================="
echo "BATCH QUARTER DOWNLOAD"
echo "=========================================="
echo "Yesterday: $YESTERDAY"
echo "Today: $TODAY"
echo "Current time: $(date)"
echo "=========================================="
echo

# Activate venv if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Function to download a quarter
download_q() {
    local quarter=$1
    local date=$2
    local description=$3
    
    echo ""
    echo "=========================================="
    echo "DOWNLOADING: $description"
    echo "=========================================="
    echo ""
    
    python3 "$SCRIPT_DIR/download_quarter.py" "$quarter" --date "$date" || {
        echo "ERROR: Failed to download Q$quarter for $date"
        exit 1
    }
    
    echo ""
    echo "✅ Completed: $description"
    echo ""
}

# 1. Yesterday's Q3 (noon-6pm)
echo "Step 1/4: Yesterday's Q3 (noon-6pm)"
download_q 3 "$YESTERDAY" "Yesterday Q3 (noon-6pm)"

# 2. Yesterday's Q4 (6pm-midnight)
echo "Step 2/4: Yesterday's Q4 (6pm-midnight)"
download_q 4 "$YESTERDAY" "Yesterday Q4 (6pm-midnight)"

# 3. Today's Q1 (midnight-6am)
echo "Step 3/4: Today's Q1 (midnight-6am)"
download_q 1 "$TODAY" "Today Q1 (midnight-6am)"

# 4. Today's Q2 (6am-noon) - wait until after noon
echo "Step 4/4: Today's Q2 (6am-noon)"
CURRENT_HOUR=$(date +"%H" | sed 's/^0//')  # Remove leading zero

if [ "$CURRENT_HOUR" -lt 12 ]; then
    MINUTES_UNTIL_NOON=$(( (12 - CURRENT_HOUR) * 60 - $(date +"%M") ))
    echo "Current time is before noon. Waiting until 12:00 PM ET..."
    echo "Waiting $MINUTES_UNTIL_NOON minutes..."
    sleep $((MINUTES_UNTIL_NOON * 60))
fi

download_q 2 "$TODAY" "Today Q2 (6am-noon)"

echo ""
echo "=========================================="
echo "✅ ALL QUARTERS DOWNLOADED"
echo "=========================================="
echo ""
echo "Downloaded:"
echo "  - Yesterday Q3 (noon-6pm)"
echo "  - Yesterday Q4 (6pm-midnight)"
echo "  - Today Q1 (midnight-6am)"
echo "  - Today Q2 (6am-noon)"
echo ""

