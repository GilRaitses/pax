# Image Organization and Manifest Guide

## Overview

The image organization system downloads and organizes all collected images by day, creating a comprehensive manifest YAML file designed for easy visualization and analysis.

## Quick Start

### Organize Local Images

```bash
cd ~/pax
source venv/bin/activate

# Organize images from local collection (copies files)
python -m pax.scripts.organize_local_images \
    --images-dir data/raw/images \
    --metadata-dir data/raw/metadata \
    --output-dir data/organized_images \
    --manifest-path data/image_manifest.yaml \
    --copy
```

### Download from GCS

If you have images in Google Cloud Storage:

```bash
python -m pax.scripts.download_images \
    --bucket pax-nyc-images \
    --prefix images \
    --output-dir data/downloaded_images \
    --manifest-path data/image_manifest.yaml
```

### Visualize Collection

```bash
# Generate all visualizations
python -m pax.scripts.visualize_collection data/image_manifest.yaml \
    --output-dir data/visualizations \
    --summary
```

## Manifest Structure

The manifest YAML includes:

### Metadata Section
- Collection period (start/end dates, total days)
- Total cameras and images
- Generation timestamp

### Collection Stats
- Date range covered
- Images per date
- Dates collected

### Cameras Section
For each camera:
- **camera_id**: Unique identifier
- **total_images**: Count of images
- **time_range**: 
  - `earliest`: First image timestamp
  - `latest`: Last image timestamp
  - `duration_hours`: Time span in hours
  - `duration_days`: Time span in days
- **images_by_date**: Count of images per day
- **images**: List of all images with:
  - `timestamp`: ISO format timestamp
  - `timestamp_str`: Filename-friendly format (YYYYMMDDTHHMMSS)
  - `date`: Date string (YYYY-MM-DD)
  - `local_path`: Path to organized image
  - `source_path`: Original path
  - `image_url`: Original API URL
  - `captured_at`: Capture timestamp
  - `size_bytes`: File size

### Completion Stats
For each camera:
- **actual_images**: Number collected
- **expected_images**: Expected based on 30-min intervals
- **percentage_complete**: Completion percentage

## Directory Structure

```
data/
├── organized_images/
│   ├── 2025-11-03/
│   │   ├── camera-id1_20251103T120000.jpg
│   │   ├── camera-id2_20251103T120000.jpg
│   │   └── ...
│   ├── 2025-11-04/
│   │   └── ...
│   └── ...
├── image_manifest.yaml
└── visualizations/
    ├── images_over_time.png
    ├── completion_by_camera.png
    ├── images_per_camera.png
    └── time_coverage.png
```

## Visualization Scripts

The `visualize_collection.py` script generates:

1. **images_over_time.png**: Collection volume over time
2. **completion_by_camera.png**: Completion percentage per camera
3. **images_per_camera.png**: Total images per camera
4. **time_coverage.png**: Time range coverage per camera

### Using the Manifest in Python

```python
import yaml

# Load manifest
with open('data/image_manifest.yaml') as f:
    manifest = yaml.safe_load(f)

# Access metadata
metadata = manifest['metadata']
print(f"Total images: {metadata['total_images']}")
print(f"Collection period: {metadata['collection_period']['start_date']} to {metadata['collection_period']['end_date']}")

# Access camera data
cameras = manifest['cameras']
for camera_id, cam_data in cameras.items():
    print(f"Camera {camera_id}: {cam_data['total_images']} images")
    print(f"  Time range: {cam_data['time_range']['earliest']} to {cam_data['time_range']['latest']}")
    print(f"  Completion: {manifest['completion_stats'][camera_id]['percentage_complete']}%")

# Access completion stats
completion = manifest['completion_stats']
for camera_id, stats in completion.items():
    print(f"{camera_id}: {stats['percentage_complete']}% complete ({stats['actual_images']}/{stats['expected_images']})")

# Access images by date
stats = manifest['collection_stats']
for date, count in stats['images_per_date'].items():
    print(f"{date}: {count} images")
```

## Options

### organize_local_images.py

- `--images-dir`: Source images directory (default: from settings)
- `--metadata-dir`: Source metadata directory (default: from settings)
- `--output-dir`: Output directory (default: `data/organized_images`)
- `--manifest-path`: Manifest output path (default: `data/image_manifest.yaml`)
- `--copy`: Copy instead of move (preserves originals)
- `--dry-run`: Show what would be done without making changes

### download_images.py

- `--bucket`: GCS bucket name (default: from settings)
- `--prefix`: GCS prefix/folder (default: `images`)
- `--output-dir`: Output directory (default: `data/downloaded_images`)
- `--manifest-path`: Manifest output path (default: `data/image_manifest.yaml`)
- `--dry-run`: List files without downloading

### visualize_collection.py

- `manifest`: Path to manifest YAML (required)
- `--output-dir`: Directory to save plots (default: show plots)
- `--summary`: Print summary report

## Example Workflow

```bash
# 1. Organize existing local images
python -m pax.scripts.organize_local_images --copy

# 2. Generate visualizations
python -m pax.scripts.visualize_collection data/image_manifest.yaml \
    --output-dir data/visualizations \
    --summary

# 3. Check completion stats
python -c "
import yaml
with open('data/image_manifest.yaml') as f:
    m = yaml.safe_load(f)
completion = m['completion_stats']
avg = sum(s['percentage_complete'] for s in completion.values()) / len(completion)
print(f'Average completion: {avg:.2f}%')
"
```

## Notes

- Images are organized by date (YYYY-MM-DD subdirectories)
- Filenames include camera ID and timestamp for easy identification
- Manifest includes both local paths and original GCS/source paths
- Completion percentage assumes 30-minute collection intervals
- The manifest is designed to be easily parsed by Python scripts for analysis

