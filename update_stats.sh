#!/usr/bin/env bash
# Update stats.json with current collection data

set -e

cd "$(dirname "$0")"
source venv/bin/activate

python3 << 'EOF'
import yaml
import json
from pathlib import Path

# Load cameras manifest
with open('cameras.yaml') as f:
    manifest = yaml.safe_load(f)

# Count actual files
metadata_root = Path('data/raw/metadata')
total_metadata = 0
camera_counts = {}
latest_capture = None

if metadata_root.exists():
    for camera_dir in metadata_root.iterdir():
        if not camera_dir.is_dir() or camera_dir.name.startswith('batch_'):
            continue
        camera_id = camera_dir.name
        count = len(list(camera_dir.glob('*.json')))
        camera_counts[camera_id] = {'count': count, 'lastCapture': None}
        total_metadata += count
        
        # Find latest capture
        for meta_file in camera_dir.glob('*.json'):
            try:
                with open(meta_file) as f:
                    data = json.load(f)
                    capture_time = data.get('captured_at', '')
                    if capture_time:
                        if not camera_counts[camera_id]['lastCapture'] or capture_time > camera_counts[camera_id]['lastCapture']:
                            camera_counts[camera_id]['lastCapture'] = capture_time
                        if not latest_capture or capture_time > latest_capture:
                            latest_capture = capture_time
            except:
                pass

# Create stats object
stats = {
    'totalImages': total_metadata,
    'activeCameras': len(manifest['cameras']),
    'latestCapture': latest_capture,
    'cameraCounts': camera_counts,
    'storageInfo': f'{total_metadata} metadata files across {len(camera_counts)} cameras'
}

# Save stats
with open('docs/stats.json', 'w') as f:
    json.dump(stats, f, indent=2)

print(f'Updated stats.json: {stats["totalImages"]} images, {stats["activeCameras"]} cameras')
if latest_capture:
    print(f'Latest capture: {latest_capture[:19]}')
EOF

# Commit if git is available
if git rev-parse --git-dir > /dev/null 2>&1; then
    git add docs/stats.json
    git commit -m "Update collection stats" 2>/dev/null || echo "No changes to commit"
    git push 2>/dev/null || echo "Could not push (remote may not be configured)"
fi

