# Camera Collection Manifest

## Study Area

**Project:** Energetic Pathfinding and Perceptual Heuristics in Manhattan Navigation  
**CIS 667 Term Project** - Syracuse University

### Geographic Scope

This project focuses on the **Grand Central to Carnegie Hall corridor** in Midtown Manhattan:

- **Start Point:** Grand Central Terminal (42nd St & Park Ave)
- **End Point:** Carnegie Hall (57th St & 7th Ave)
- **Bounding Box:** 40th-59th Streets, Lexington Ave to 8th Ave
- **Coverage:** 40 cameras (NOT all 950+ NYC cameras)

### Why This Corridor?

The corridor spans key Manhattan areas with diverse traffic characteristics:
- **Midtown Core:** High pedestrian density, commercial district
- **Theater District:** Variable crowding, entertainment venues
- **East Side:** Residential/commercial mix
- **West Side:** Park access, cultural venues

## Camera Manifest

The `cameras.yaml` file contains **40 cameras** organized by:

### By Area
- **Midtown Core:** 18 cameras (5th Ave, Madison, Rockefeller Plaza)
- **East Side:** 10 cameras (Park Ave, Lexington, 3rd Ave)
- **West Midtown:** 5 cameras (6th Ave/Avenue of the Americas)
- **Theater District:** 5 cameras (7th Ave, Broadway)
- **West Side:** 2 cameras (8th Ave, Central Park)

### By Priority
- **High Priority:** 21 cameras (major avenues, key intersections)
- **Medium Priority:** 19 cameras (secondary streets)

## Collection Schedule

- **Frequency:** Every 30 minutes
- **Active Hours:** 6:00 AM - 10:00 PM (Eastern Time)
- **Data Captured:**
  - Traffic camera images
  - Vision AI analysis (pedestrian density, violations, infrastructure)
  - Timestamp and location metadata

## Usage

### Collect from Manifest Cameras

```bash
cd ~/pax
source venv/bin/activate

# Collect using the manifest
python -m pax.scripts.collect_manifest

# Options:
python -m pax.scripts.collect_manifest --skip-images  # Metadata only
python -m pax.scripts.collect_manifest --manifest custom_cameras.yaml  # Custom list
```

### View Live Dashboard

```bash
# Start the stats API server
python -m pax.scripts.stats_api

# Open in browser:
# http://localhost:8000/
```

The dashboard shows:
- Total images collected
- Active cameras (40 in corridor)
- Latest capture time
- Per-camera statistics

## Manifest File Structure

`cameras.yaml` format:

```yaml
project:
  name: "Pax NYC - Grand Central to Carnegie Hall Corridor"
  description: "Energetic pathfinding and perceptual heuristics study"
  study_area:
    start: "Grand Central Terminal (42nd & Park)"
    goal: "Carnegie Hall (57th & 7th Ave)"
    bounds: "40th-59th Streets, Lexington Ave to 8th Ave"

schedule:
  interval_minutes: 30
  active_hours:
    start: "06:00"
    end: "22:00"
  timezone: "America/New_York"

cameras:
  - id: "camera-uuid-here"
    name: "5 Ave @ 42 St"
    area: "Midtown Core"
    latitude: 40.753492
    longitude: -73.980897
    priority: "high"
  # ... 39 more cameras
```

## Finding Additional Cameras

To explore cameras in other areas:

```bash
# List all available cameras
python -m pax.scripts.collect --dry-run --max-cameras 50

# Filter to specific area
python -m pax.scripts.collect --dry-run | grep "Midtown\|Times Square"
```

## Data Storage

Collected data is stored in:

- **Local:** `data/raw/images/` and `data/raw/metadata/`
- **Cloud:** `gs://pax-nyc-images/images/` (if GCS configured)
- **Warehouse:** `data/warehouse/snapshots/*.parquet` (daily aggregates)

## Important Notes

- **DO NOT** collect from all 950+ cameras
- Stick to the 40-camera corridor for this project
- This focuses computational resources on the study area
- Aligns with CIS 667 term project scope
- Reduces GCS storage costs

## Cloud Run Deployment

For automated collection every 30 minutes:

```bash
./infra/bootstrap_collection.sh
```

This deploys a Cloud Run job that:
1. Collects from the 40 corridor cameras
2. Runs every 30 minutes (configurable)
3. Uploads to GCS
4. Updates the warehouse

## Questions?

See the main README or CIS 667 term project proposal for more details.

