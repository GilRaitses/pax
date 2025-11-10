# Cloud Run Collector V2 Deployment

## Overview

New deployment system that:
1. Generates numbered camera manifest matching partitioning map order
2. Cancels old jobs/schedulers
3. Deploys new Cloud Run Job with numbered cameras
4. Uses direct HTTP scheduler (no Pub/Sub)

## Files Created

### Scripts
- `src/pax/scripts/generate_numbered_camera_manifest.py` - Generates numbered manifest
- `infra/cloudrun/deploy_collector_v2.sh` - New deployment script
- `infra/cloudrun/entrypoint_v2.sh` - New container entrypoint

### Updated
- `src/pax/scripts/collect_manifest.py` - Now supports JSON manifests

## Camera Numbering

Cameras are numbered 1-82 in the same order as the partitioning map:
- Filters to purple corridor (34th-66th St, 3rd-9th/Amsterdam)
- Uses same filtering logic as `draw_corridor_border.py`
- Numbers match visualization exactly

## Deployment Steps

1. **Generate numbered manifest:**
   ```bash
   python3 -m src.pax.scripts.generate_numbered_camera_manifest \
     --output data/corridor_cameras_numbered.json
   ```

2. **Deploy new collector:**
   ```bash
   cd infra/cloudrun
   ./deploy_collector_v2.sh \
     --project pax-nyc \
     --region us-central1 \
     --bucket pax-nyc-images
   ```

## What Gets Cancelled

- Old job: `pax-collector`
- Old scheduler: `pax-collector-schedule`
- Pub/Sub topic: `run-jobs-trigger` (no longer needed)

## What Gets Created

- New job: `pax-collector-v2`
- New scheduler: `pax-collector-v2-schedule`
- Direct HTTP trigger (no Pub/Sub)

## Manifest Format

```json
{
  "metadata": {
    "total_cameras": 82,
    "corridor": {
      "boundary": "34th-66th St, 3rd-9th/Amsterdam",
      "corners": {...}
    }
  },
  "cameras": [
    {
      "number": 1,
      "id": "camera-id-1",
      "name": "Camera Name",
      "latitude": 40.xxx,
      "longitude": -73.xxx
    },
    ...
  ]
}
```

## Benefits

1. **Consistent numbering** - Cameras always collected in same order
2. **Matches visualization** - Numbers match partitioning map exactly
3. **Direct HTTP trigger** - More reliable than Pub/Sub
4. **Clean deployment** - Removes old broken setup

