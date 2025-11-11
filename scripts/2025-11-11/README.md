# Scripts for 2025-11-11

## Overview
Daily scripts folder for November 11, 2025.

## Scripts Created Today

### `cinnamoroll_monitor.py`
Cinnamoroll-themed process status monitor with ASCII animation.

**Features:**
- Bouncing Cinnamoroll ASCII art characters (flipbook animation)
- Large ASCII numbers and letters for counters
- Updates every 1.5 seconds
- Cinnamoroll color theme (blue, pink, mint, cream)
- Monitors images and features extraction progress
- Can tail log files

**Usage:**
```bash
python3 scripts/2025-11-11/cinnamoroll_monitor.py

# Or launch in new window:
./scripts/2025-11-11/open_cinnamoroll_monitor.sh
```

### `download_quarter.py`
Downloads images for a specific 6-hour quarter of a day.

**Quarters:**
- Q1: 00:00-05:59 (midnight-6am)
- Q2: 06:00-11:59 (6am-noon)
- Q3: 12:00-17:59 (noon-6pm)
- Q4: 18:00-23:59 (6pm-midnight)

**Usage:**
```bash
# Download yesterday's Q3 (noon-6pm)
python3 scripts/2025-11-11/download_quarter.py 3 --date 2025-11-10

# Download today's Q1 (midnight-6am)
python3 scripts/2025-11-11/download_quarter.py 1

# Download today's Q2 (6am-noon)
python3 scripts/2025-11-11/download_quarter.py 2
```

### `download_batch_quarters.sh`
Batch script to download multiple quarters in sequence:
1. Yesterday's Q3 (noon-6pm)
2. Yesterday's Q4 (6pm-midnight)
3. Today's Q1 (midnight-6am)
4. Today's Q2 (6am-noon) - waits until after noon

**Usage:**
```bash
./scripts/2025-11-11/download_batch_quarters.sh
```

## Notes
- Download script was updated yesterday to handle partial files and filter by time range
- Collection system is running every 30 minutes via Cloud Scheduler
- Quarters allow organized batch downloads of 6-hour periods

