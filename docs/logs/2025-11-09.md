# Development Log: November 9, 2025

## Accomplishments

### 1. Problem Space Visualization (Red Zone - Intersection Scale)
**Script:** `problem_space_partition.py` (master script for partition maps)

**Features Implemented:**
- Created focused visualization of the constrained problem space (red boundary: 40th-61st St, Lex-8th/CPW)
- Deep purple Voronoi tessellation lines clipped precisely to red boundary
- Street grid with fainter grey lines for regular streets, deep yellow for major avenues
- Major cross streets (42nd, 45th, 47th, 49th, 52nd, 55th, 57th) highlighted in yellow
- Avenue labels on top and bottom x-axes with diagonal slants
- Street labels on left and right y-axes with proper formatting:
  - Left side: "W. {number}th St." format
  - Right side: "E. {number}th St." format
  - Special handling for 49th Street (E vs W distinction)
- START (Grand Central) and GOAL (Carnegie Hall) markers with connecting dashed lines
- Central Park and Bryant Park labeled and filled with green
- North arrow positioned outside plot frame
- Title: "Problem Space: Multi-Scale Coverage Zones"

**Key Technical Details:**
- Street lines clipped to extend only 1cm beyond red boundary on left/right
- Affine transformation applied to align streets horizontally and avenues vertically
- Voronoi tessellation uses 82 cameras from purple corridor
- All labels properly positioned to avoid overlap with boundaries

**Output:** `problem_space.png`

### 2. Camera Corridor Visualization (Purple Zone - Camera Zone Scale)
**Script:** `camera_corridor_partition.py`

**Features Implemented:**
- Wider camera corridor visualization (purple boundary: 34th-66th St, 3rd-9th/Amsterdam)
- Shows all 82 cameras within purple corridor bounds (including boundary cameras)
- Numbered camera markers for cameras in purple zone
- Voronoi tessellation computed for all cameras in purple corridor
- Problem space (red boundary) nested within camera corridor
- START and GOAL markers correctly positioned
- Street grid and labels similar to problem space visualization

**Key Technical Details:**
- Camera filtering includes cameras on or very close to purple boundary (buffer tolerance)
- Corner cameras explicitly checked and included
- Voronoi edges clipped to purple boundary
- Transformation applied consistently across all elements

**Output:** `voronoi_tessellation_final.png`

### 3. Multi-Scale Resolution System

**Two Scales Defined:**

1. **Camera Zone Scale (Purple Zone)**
   - Boundary: 34th-66th St, 3rd-9th/Amsterdam
   - Purpose: Extended corridor for Pareto front analysis
   - Cameras: 82 cameras in corridor
   - Use case: Multi-scale resolution for determining Pareto-optimal solutions

2. **Intersection Scale (Red Zone)**
   - Boundary: 40th-61st St, Lex-8th/CPW
   - Purpose: Constrained problem space for graph search
   - Intersections: 161 intersection nodes
   - Use case: Focused search space between START and GOAL

### 4. Script Organization

**Master Script:** `problem_space_partition.py`
- Primary script for creating partition maps
- Can be adapted for different scales
- Well-documented and modular

**Supporting Script:** `camera_corridor_partition.py`
- Shows wider camera corridor context
- Demonstrates multi-scale relationship

### 5. Documentation

- Caption guides created for both visualizations
- Scripts saved with clear naming conventions
- Log entry documenting all accomplishments
- Folder structure organized by date

## Technical Notes

### Coordinate Transformations
- Affine transformation matrix computed to align streets horizontally and avenues vertically
- Transformation applied consistently to all geometries (streets, cameras, intersections, boundaries)
- X-axis flipped to correct east/west orientation

### Camera Filtering
- Buffer tolerance: 0.0003 degrees (~33 meters) for boundary inclusion
- Corner tolerance: 0.0005 degrees (~55 meters) for corner cameras
- Explicit checks for cameras on boundary lines

### Label Positioning
- Avenue labels: Diagonal slants (45° bottom, -45° top)
- Street labels: Diagonal slants (-45° left, 45° right)
- Labels positioned so last letter touches axis line
- Proper offsets to avoid overlap with boundaries

### 6. Cloud Deployment System

**Deployment Scripts:**
- `deploy_collector_v2.sh` - Deploys Cloud Run job with numbered camera manifest
- `deploy_reminder.sh` - Deploys daily email reminder Cloud Function
- `generate_numbered_camera_manifest.py` - Creates numbered manifest (1-82) matching visualization

**Deployment Accomplishments:**
- ✅ Deployed `pax-collector-v2` Cloud Run job
- ✅ Created `pax-collector-v2-schedule` (every 30 minutes)
- ✅ Optimized build size: 1.4 GiB → 10.3 MiB (created `.gcloudignore`)
- ✅ Collection started: November 9, 2025
- ✅ Test execution successful
- ✅ 82 cameras numbered 1-82 matching partitioning map

**Collection Configuration:**
- **Cameras:** 82 (purple corridor: 34th-66th St, 3rd-9th/Amsterdam)
- **Schedule:** Every 30 minutes
- **Rate:** 48 images/camera/day = 3,936 images/day total
- **Target:** 672 images/camera over 14 days = 55,104 total images
- **Storage:** ~5.38 GB estimated
- **GCS Bucket:** `gs://pax-nyc-images/images/`

**Build Optimization:**
- Created `.gcloudignore` to exclude:
  - `docs/` (929MB visualization images)
  - `venv/` (553MB)
  - `data/raw/images/` (collected images)
  - All PNG/JPEG files
- Build now only includes source code and manifest

### 7. Dashboard and Statistics

**Updated Dashboard (`docs/index.html`):**
- Shows live collection statistics from GCS
- Displays 82 numbered cameras (1-82)
- Shows total images, today's images, collection period
- Auto-refreshes every 30 seconds
- Works with GitHub Pages (static stats.json)

**New Scripts:**
- `generate_gcs_stats.py` - Generates collection stats from GCS bucket
- Outputs `docs/stats.json` for static serving
- Includes camera counts, dates, collection period

**Stats Generated:**
- Total images: 169 (as of Nov 10)
- Collection period: Nov 5 - Nov 10, 2025
- Active cameras: 82

## Future Work

- Create intersection-scale visualization script
- Develop unified script that can generate visualizations at any scale
- Add configuration files for different scale definitions
- Create comparison visualizations showing all scales together
- Set up daily email reminders (deploy_reminder.sh ready)
- Create automated stats refresh workflow

