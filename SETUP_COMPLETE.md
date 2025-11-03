# Pax NYC Setup Complete

## What's Been Created

### 1. Camera Manifest System (`cameras.yaml`)
- **40 cameras** in the Grand Central-Carnegie Hall corridor
- Geographic bounds: 40th-59th Streets, Lexington to 8th Ave
- Organized by area (Midtown Core, East Side, Theater District, etc.)
- Priority levels (high/medium) for key intersections

### 2. Live Dashboard (`docs/index.html`)
- Real-time image collection statistics
- Per-camera capture counts
- Auto-refreshes every 30 seconds
- Clean, modern UI with area breakdown

### 3. Collection Scripts
- `pax.scripts.collect_manifest` - Collect from manifest cameras only
- `pax.scripts.stats_api` - Serve dashboard + API endpoints
- `START_DASHBOARD.sh` - One-click dashboard launch

### 4. Documentation
- `CAMERA_MANIFEST.md` - Complete guide to camera selection
- `cameras.yaml` - Machine-readable manifest
- `corridor_cameras.json` - Raw camera data

## Quick Start

### View the Dashboard

```bash
cd ~/pax
./START_DASHBOARD.sh
```

Then open: http://localhost:8000

### Collect Data from Corridor Cameras

```bash
cd ~/pax
source venv/bin/activate

# Collect images and metadata
python -m pax.scripts.collect_manifest

# Metadata only (faster)
python -m pax.scripts.collect_manifest --skip-images
```

### Deploy to Cloud Run (Automated Collection)

```bash
cd ~/pax

export PAX_PROJECT=pax-nyc
export PAX_REGION=us-central1
export PAX_BUCKET=pax-nyc-images
export GOOGLE_APPLICATION_CREDENTIALS=$HOME/pax-ingest-key.json

./infra/bootstrap_collection.sh
```

Note: You'll need to update the Cloud Run deployment to use `collect_manifest` instead of the generic collect script.

## Dashboard Features

The live dashboard shows:

1. **Total Images**: Count of all captured frames
2. **Active Cameras**: 40 cameras in the corridor
3. **Latest Capture**: Timestamp of most recent collection
4. **Collection Rate**: 30-minute intervals
5. **Per-Camera Details**:
   - Camera name and location
   - Priority level (high/medium)
   - Area (Midtown Core, East Side, etc.)
   - Image count
   - Last capture time

## Study Area Details

**Grand Central to Carnegie Hall Corridor**

- **Start:** Grand Central Terminal (42nd St & Park Ave)
- **Goal:** Carnegie Hall (57th St & 7th Ave)
- **Coverage:** 40 cameras across 5 Manhattan areas

### Camera Breakdown

| Area | Cameras | Key Locations |
|------|---------|---------------|
| Midtown Core | 18 | 5th Ave, Madison, Rockefeller Plaza |
| East Side | 10 | Park Ave, Lexington, 3rd Ave |
| West Midtown | 5 | 6th Ave/Avenue of the Americas |
| Theater District | 5 | 7th Ave, Broadway |
| West Side | 2 | 8th Ave, Central Park |

## API Endpoints

When `stats_api` is running:

- `GET /` - Dashboard UI
- `GET /api/stats` - Collection statistics (JSON)
- `GET /api/manifest` - Camera manifest (JSON)

## Next Steps

### 1. Test Collection
```bash
python -m pax.scripts.collect_manifest --skip-images
```

Should collect metadata from 40 cameras in ~1-2 minutes.

### 2. View Results
```bash
./START_DASHBOARD.sh
# Open http://localhost:8000
```

### 3. Build Warehouse
```bash
python -m pax.scripts.warehouse
```

Creates daily parquet files in `data/warehouse/snapshots/`.

### 4. Deploy Cloud Run
Update `infra/cloudrun/entrypoint.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

exec python -m pax.scripts.collect_manifest --skip-images
```

Then run `./infra/bootstrap_collection.sh`.

## File Locations

```
/Users/gilraitses/pax/
├── cameras.yaml                 # 40-camera manifest
├── corridor_cameras.json        # Raw camera data
├── CAMERA_MANIFEST.md          # Documentation
├── START_DASHBOARD.sh          # Launch dashboard
├── docs/
│   └── index.html              # Dashboard UI
├── src/pax/scripts/
│   ├── collect_manifest.py     # Manifest-based collection
│   └── stats_api.py            # Dashboard API server
└── data/
    ├── raw/
    │   ├── images/             # Captured JPEGs
    │   └── metadata/           # JSON metadata
    └── warehouse/
        └── snapshots/          # Parquet files
```

## Important Notes

- ✅ **Only 40 cameras** in the corridor (not all 950+)
- ✅ Aligned with CIS 667 term project scope
- ✅ Grand Central → Carnegie Hall focus area
- ✅ API requires no authentication (NYCTMC is public)
- ✅ Dashboard auto-refreshes every 30 seconds
- ✅ Collection runs every 30 minutes (configurable)

## Troubleshooting

### Dashboard shows "No data collected yet"
Run a collection first:
```bash
python -m pax.scripts.collect_manifest --skip-images
```

### API returns 404
Make sure you're running the stats API:
```bash
python -m pax.scripts.stats_api
```

### Collection fails
Check your virtual environment:
```bash
source venv/bin/activate
pip install -e .
```

## Questions?

- See `CAMERA_MANIFEST.md` for camera selection details
- See `README.md` for general Pax documentation
- See CIS 667 term project proposal for research context

---

**Setup completed:** November 3, 2025  
**Study area:** Grand Central-Carnegie Hall corridor, Manhattan  
**Cameras:** 40 (high-priority intersections)  
**Dashboard:** http://localhost:8000 (when stats_api is running)

