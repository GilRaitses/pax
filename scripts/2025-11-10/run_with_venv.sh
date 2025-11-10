#!/bin/bash
# Wrapper script to run Python scripts with the venv activated

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV_PYTHON="$PROJECT_ROOT/venv/bin/python"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "ERROR: Virtual environment not found at $PROJECT_ROOT/venv"
    echo "Please create it with: python3 -m venv venv && source venv/bin/activate && pip install -e ."
    exit 1
fi

# Run the script with venv Python
exec "$VENV_PYTHON" "$@"

