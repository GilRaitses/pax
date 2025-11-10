#!/usr/bin/env bash
# Copy figure generation scripts to proposal and report directories

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "Copying figure scripts to proposal and report directories..."

# Copy all Python scripts
for script in "$SCRIPT_DIR"/*.py; do
    if [ -f "$script" ]; then
        script_name=$(basename "$script")
        echo "  Copying $script_name..."
        cp "$script" "$PROJECT_ROOT/docs/proposal/scripts/"
        cp "$script" "$PROJECT_ROOT/docs/report/scripts/"
    fi
done

# Copy README
if [ -f "$SCRIPT_DIR/README.md" ]; then
    echo "  Copying README.md..."
    cp "$SCRIPT_DIR/README.md" "$PROJECT_ROOT/docs/proposal/scripts/"
    cp "$SCRIPT_DIR/README.md" "$PROJECT_ROOT/docs/report/scripts/"
fi

echo "✅ All scripts copied successfully"
