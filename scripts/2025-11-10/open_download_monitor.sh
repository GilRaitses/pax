#!/bin/bash
# Open download progress monitor in a new terminal window

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Default values
LOCAL_DIR="${1:-data/raw/images}"
EXPECTED_TOTAL="${2:-0}"
REFRESH_INTERVAL="${3:-2.0}"
DATE_FILTER="${4:-}"

# Detect OS and open appropriate terminal
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS - use Terminal.app or iTerm2
    if command -v iterm2 &> /dev/null || [ -d "/Applications/iTerm.app" ]; then
        # Use iTerm2 if available
        osascript <<EOF
tell application "iTerm"
    activate
    create window with default profile
    tell current session of current window
        write text "cd '$PROJECT_ROOT' && python3 '$SCRIPT_DIR/monitor_download_progress.py' --local-dir '$LOCAL_DIR' --expected-total $EXPECTED_TOTAL --refresh-interval $REFRESH_INTERVAL${DATE_FILTER:+ --date-filter $DATE_FILTER}"
    end tell
end tell
EOF
    else
        # Use Terminal.app
        osascript <<EOF
tell application "Terminal"
    activate
    do script "cd '$PROJECT_ROOT' && python3 '$SCRIPT_DIR/monitor_download_progress.py' --local-dir '$LOCAL_DIR' --expected-total $EXPECTED_TOTAL --refresh-interval $REFRESH_INTERVAL${DATE_FILTER:+ --date-filter $DATE_FILTER}"
end tell
EOF
    fi
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux - try common terminals
    if command -v gnome-terminal &> /dev/null; then
        gnome-terminal -- bash -c "cd '$PROJECT_ROOT' && python3 '$SCRIPT_DIR/monitor_download_progress.py' --local-dir '$LOCAL_DIR' --expected-total $EXPECTED_TOTAL --refresh-interval $REFRESH_INTERVAL${DATE_FILTER:+ --date-filter $DATE_FILTER}; exec bash"
    elif command -v xterm &> /dev/null; then
        xterm -e "cd '$PROJECT_ROOT' && python3 '$SCRIPT_DIR/monitor_download_progress.py' --local-dir '$LOCAL_DIR' --expected-total $EXPECTED_TOTAL --refresh-interval $REFRESH_INTERVAL${DATE_FILTER:+ --date-filter $DATE_FILTER}"
    else
        echo "ERROR: No suitable terminal found. Please run manually:"
        echo "  python3 $SCRIPT_DIR/monitor_download_progress.py --local-dir '$LOCAL_DIR' --expected-total $EXPECTED_TOTAL --refresh-interval $REFRESH_INTERVAL"
        exit 1
    fi
else
    echo "ERROR: Unsupported OS: $OSTYPE"
    exit 1
fi

