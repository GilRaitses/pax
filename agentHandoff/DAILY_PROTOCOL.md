# Daily Agent Handoff Protocol

## Daily Structure Setup

### Every New Day:

**1. Get System Date**
```bash
date +"%Y-%m-%d"
```

**2. Create Log Entry**
```bash
cd /Users/gilraitses/pax
# Create: docs/logs/YYYY-MM-DD.md
```

**3. Create Daily Scripts Folder**
```bash
# Create: scripts/YYYY-MM-DD/
# ALL scripts created/modified today MUST go in this folder
# Never create scripts in scripts/ root - always use daily folders
```

**4. Update Agent Handoff**
```bash
# Review and update agentHandoff/DAILY_PROTOCOL.md if needed
# Create any new handoff files in agentHandoff/
```

---

## File Naming Convention

**All handoff files:**
```
<author>_<recipient>_<timestamp>_<subject-4-5-words>.md

Where:
- author: Agent codename (lowercase-hyphenated)
- recipient: Target agent codename or "next-agent"
- timestamp: YYYYMMDD-HHMMSS from system (NO hallucination!)
- subject: 4-5 descriptive words (lowercase-hyphenated)
```

**Examples:**
```
composer_next-agent_20251110-091500_fix-image-viewer-gcs-access.md
composer_next-agent_20251110-143000_update-index-html-styling.md
```

---

## Required Handoff Structure

Every handoff must include:

```markdown
# Handoff: <Subject>

**From:** <author>  
**To:** <recipient>  
**Date:** YYYY-MM-DD HH:MM:SS  
**Priority:** [High/Medium/Low]  
**Status:** [Pending/In Progress/Complete/Blocked]

## Context
[What led to this handoff]

## Task/Question/Report
[The actual content]

## Deliverables (if task)
[What needs to be produced]

## Questions (if inquiry)
[Specific questions needing answers]

## Results (if completion)
[What was accomplished]

## Next Steps
[What happens after this]

---

**<Author Name>** <emoji>  
**Date:** YYYY-MM-DD HH:MM:SS
```

---

## Daily Log Requirements

**File:** `docs/logs/YYYY-MM-DD.md`

**Must include:**
- Objective for the day
- Completed work from previous day
- Current blockers
- Project milestone status
- Next steps
- Key files/scripts created or modified

**Template:**
```markdown
# Development Log - Month DD, YYYY

## Objective
[What we're trying to accomplish today]

## Carryover from [Previous Date]
[Summary of where we left off]

## Progress Today
[What got done]

### Key Accomplishments
- [Specific task 1]
- [Specific task 2]

### Files Created/Modified
- `path/to/file.py` - [description]
- `path/to/file.md` - [description]

## Blockers
[What's preventing progress]

## Project Status

### Data Collection
- Cloud Run Job: [status]
- Scheduler: [status]
- Images Collected: [count]
- Latest Capture: [timestamp]

### Visualization
- Problem Space Map: [status]
- Camera Corridor Map: [status]
- Index Page: [status]

### Infrastructure
- Deployment: [status]
- GCS Bucket: [status]
- Stats Generation: [status]

## Next Steps
[What's next]

---

**Status:** [summary]  
**Next Session:** [what to tackle]
```

---

## Project-Specific Context

### Key Directories
- `src/pax/` - Main source code
- `src/pax/scripts/` - Python scripts
- `src/pax/data_collection/` - Data collection logic
- `docs/logs/YYYY-MM-DD/` - Daily logs and outputs
- `docs/logs/YYYY-MM-DD/scripts/` - Scripts for the day
- `docs/logs/YYYY-MM-DD/outputs/` - Generated figures/images
- `docs/logs/YYYY-MM-DD/captions/` - Figure captions
- `data/` - Active data files (critical files only)
- `docs/backup/` - All backup/archived folders
  - `docs/backup/data_bkup/` - Archived data files
  - `docs/backup/backup_20251105_150716/` - Historical backup
  - `docs/backup/infra_bkup/` - Archived infrastructure
  - `docs/backup/src_bkup/` - Archived source code
- `data/shapefiles/` - Shapefiles (DCM streets, parks, water)
- `infra/cloudrun/` - Cloud deployment scripts
- `agentHandoff/` - Agent handoff files

### Critical Files (Never Move)
- `data/corridor_cameras_numbered.json` - Camera manifest for deployment
- `data/corridor_cameras_numbered.yaml` - Same manifest in YAML
- `data/geojson/intersections.json` - Intersection data for visualizations

### Key Scripts (Master Scripts - Permanent)
- `src/pax/scripts/draw_problem_space.py` - Problem space visualization (red zone)
- `src/pax/scripts/draw_corridor_border.py` - Camera corridor visualization (purple zone)
- `src/pax/scripts/generate_gcs_stats.py` - Generate collection statistics
- `src/pax/scripts/generate_numbered_camera_manifest.py` - Create camera manifest
- `src/pax/scripts/package_daily_images.py` - Package daily images
- `infra/cloudrun/deploy_collector.sh` - Deploy collection system

### Daily Scripts Organization
**CRITICAL RULE: All scripts created/modified on a given day MUST be placed in `scripts/YYYY-MM-DD/`**

- **Never create scripts in `scripts/` root directory**
- **Always use daily folders: `scripts/YYYY-MM-DD/`**
- **Copy master scripts to daily folder if modifying them**
- **Include README.md in daily folder explaining what scripts do**
- **Archive daily folders - they are historical records**

**Example:**
```
scripts/
├── 2025-11-09/
│   ├── problem_space_partition.py
│   ├── camera_corridor_partition.py
│   └── README.md
├── 2025-11-10/
│   ├── migrate_data_to_backup.py
│   ├── organize_data_files.py
│   ├── MIGRATION_README.md
│   └── README.md
└── (NO scripts directly in scripts/ root!)
```

### Deployment Info
- **Project:** pax-nyc
- **GCS Bucket:** pax-nyc-images
- **Cloud Run Job:** pax-collector
- **Scheduler:** pax-collector-schedule (every 30 minutes)
- **Service Account:** pax-collector@pax-nyc.iam.gserviceaccount.com
- **Collection Rate:** 48 images/camera/day (every 30 minutes)
- **Target Zone:** Purple corridor (34th-66th St, 3rd-9th/Amsterdam)
- **Cameras:** 82 numbered cameras

---

## Status Tracking

**File:** `agentHandoff/STATUS.md` (updated daily)

Track all active handoffs:
```markdown
| From | To | Subject | Status | File |
|------|----|--------|--------|------|
| ...  | ...| ...    | ...    | ...  |
```

---

## Cross-Day References

**Referencing previous days:**
```markdown
See: docs/logs/2025-11-09/scripts/problem_space_partition.py
```

**Continuing work:**
```markdown
Continued from: 2025-11-09
Previous log: docs/logs/2025-11-09.md
```

---

## Rules

1. ✅ Always get fresh system timestamp
2. ✅ Follow exact naming convention
3. ✅ Update STATUS.md if tracking handoffs
4. ✅ Create daily log in `docs/logs/YYYY-MM-DD.md`
5. ✅ Reference related work from previous days
6. ✅ Clear deliverables and next steps
7. ✅ No hallucinated timestamps!
8. ✅ Preserve critical files in `data/`
9. ✅ Document all script changes
10. ✅ Update index.html if dashboard changes

---

## Project Milestones

### M1: Visualization System ✅
- Problem space map (red zone)
- Camera corridor map (purple zone)
- Multi-scale coverage zones

### M2: Data Collection System ✅
- Cloud Run job deployment
- Scheduled collection (every 30 min)
- GCS storage
- Numbered camera manifest

### M3: Dashboard & Stats ✅
- Index.html with live stats
- Image viewer
- Collection status display

### M4: Documentation & Organization
- Daily logs
- Script documentation
- Caption guides
- Migration tools

---

**Last Updated:** 2025-11-10  
**Purpose:** Maintain clean, traceable development workflow and agent communication
