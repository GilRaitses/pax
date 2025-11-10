# Feature Vector Schema Specification

**Created:** November 10, 2025  
**Purpose:** Define standardized empirical data structure for vision model outputs

## Overview

The `FeatureVector` schema represents a comprehensive feature vector combining spatial, visual complexity, and temporal features extracted from traffic camera images. This standardized format enables integration with the search algorithm for learned heuristic pathfinding.

## Schema Structure

The `FeatureVector` is composed of three main feature groups:

1. **Spatial Features** - Object counts and density metrics from detection models
2. **Visual Complexity Features** - Scene characteristics and environmental conditions
3. **Temporal Features** - Time-based encodings and temporal patterns

## Spatial Features

Spatial features are extracted from object detection models (YOLOv8n, Detectron2) and describe the presence and density of objects in the scene.

### Fields

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `pedestrian_count` | `int` | ≥ 0 | Number of detected pedestrians in the frame |
| `vehicle_count` | `int` | ≥ 0 | Number of detected vehicles (cars, trucks, buses, motorcycles) |
| `bicycle_count` | `int` | ≥ 0 | Number of detected bicycles |
| `total_object_count` | `int` | ≥ 0 | Total number of detected objects (all classes) |
| `pedestrian_density` | `float` | ≥ 0.0 | Pedestrian density per square meter (estimated from detection area) |
| `vehicle_density` | `float` | ≥ 0.0 | Vehicle density per square meter (estimated from detection area) |
| `crowd_density` | `float` | [0.0, 1.0] | Normalized crowd density metric (0.0 = empty, 1.0 = maximum density) |
| `object_density` | `float` | ≥ 0.0 | Overall object density (objects per square meter) |

### Calculation Notes

- **Density metrics**: Calculated from bounding box areas and estimated scene dimensions
- **Crowd density**: Normalized metric combining pedestrian count and spatial distribution
- **Object density**: Aggregate metric considering all detected objects

## Visual Complexity Features

Visual complexity features describe scene characteristics, environmental conditions, and visual quality metrics. These are derived from segmentation models (Detectron2) and scene understanding models (CLIP).

### Fields

| Field | Type | Range/Values | Description |
|-------|------|--------------|-------------|
| `scene_complexity` | `float` | [0.0, 1.0] | Normalized scene complexity score (0.0 = simple, 1.0 = highly complex) |
| `visual_noise` | `float` | [0.0, 1.0] | Visual noise indicator (0.0 = clean, 1.0 = high noise) |
| `lighting_condition` | `str` | `"daylight"`, `"twilight"`, `"night"`, `"artificial"` | Primary lighting condition in the scene |
| `lighting_brightness` | `float` | [0.0, 1.0] | Normalized lighting brightness (0.0 = dark, 1.0 = bright) |
| `weather_condition` | `str` | `"clear"`, `"cloudy"`, `"rainy"`, `"foggy"`, `"snowy"`, `"unknown"` | Weather condition inferred from visual analysis |
| `visibility_score` | `float` | [0.0, 1.0] | Normalized visibility metric (0.0 = poor visibility, 1.0 = excellent) |
| `occlusion_score` | `float` | [0.0, 1.0] | Occlusion/obstruction score (0.0 = no occlusions, 1.0 = heavily occluded) |

### Calculation Notes

- **Scene complexity**: Derived from number of objects, spatial distribution, and visual clutter
- **Visual noise**: Computed from image quality metrics and compression artifacts
- **Lighting condition**: Classified from image brightness and color temperature
- **Weather condition**: Inferred from visual cues (precipitation, fog, snow) or metadata
- **Visibility score**: Based on image clarity, contrast, and atmospheric conditions
- **Occlusion score**: Calculated from overlapping bounding boxes and segmentation masks

## Temporal Features

Temporal features encode time-based information extracted from image metadata. These features capture periodic patterns and temporal context.

### Fields

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `timestamp` | `datetime` | - | Exact timestamp when the image was captured |
| `hour` | `int` | [0, 23] | Hour of day (0-23) in local timezone |
| `minute` | `int` | [0, 59] | Minute of hour (0-59) |
| `day_of_week` | `int` | [1, 7] | Day of week (1=Monday, 7=Sunday) per ISO 8601 |
| `is_weekend` | `bool` | - | Whether the day is a weekend (Saturday or Sunday) |
| `is_rush_hour` | `bool` | - | Whether the time falls within rush hour periods (7-9 AM or 5-7 PM) |
| `time_of_day_encoding` | `float` | [0.0, 1.0] | Normalized time of day encoding (0.0 = midnight, 1.0 = next midnight) |
| `day_of_week_encoding` | `float` | [0.0, 1.0] | Normalized day of week encoding (0.0 = Monday, 1.0 = Sunday) |

### Calculation Notes

- **Time encodings**: Normalized cyclic encodings for machine learning compatibility
  - `time_of_day_encoding = (hour * 60 + minute) / 1440.0`
  - `day_of_week_encoding = (day_of_week - 1) / 7.0`
- **Rush hour**: Defined as 7:00-9:00 AM and 5:00-7:00 PM on weekdays
- **Weekend**: Saturday (6) or Sunday (7)

## Optional Features

### CLIP Embeddings

| Field | Type | Description |
|-------|------|-------------|
| `clip_embedding` | `list[float]` \| `None` | Optional CLIP image embedding vector (512 or 768 dimensions) |
| `semantic_scores` | `dict[str, float]` \| `None` | Optional CLIP similarity scores for semantic prompts (e.g., `{"busy_intersection": 0.85, "quiet_street": 0.12}`) |

### Model Metadata

| Field | Type | Description |
|-------|------|-------------|
| `model_metadata` | `dict[str, str \| float \| int]` \| `None` | Optional metadata about vision models used (versions, confidence thresholds, etc.) |

## Example Feature Vector

```json
{
  "spatial": {
    "pedestrian_count": 12,
    "vehicle_count": 8,
    "bicycle_count": 3,
    "total_object_count": 23,
    "pedestrian_density": 0.15,
    "vehicle_density": 0.08,
    "crowd_density": 0.65,
    "object_density": 0.23
  },
  "visual_complexity": {
    "scene_complexity": 0.72,
    "visual_noise": 0.15,
    "lighting_condition": "daylight",
    "lighting_brightness": 0.85,
    "weather_condition": "clear",
    "visibility_score": 0.92,
    "occlusion_score": 0.18
  },
  "temporal": {
    "timestamp": "2025-11-10T14:30:00-05:00",
    "hour": 14,
    "minute": 30,
    "day_of_week": 1,
    "is_weekend": false,
    "is_rush_hour": false,
    "time_of_day_encoding": 0.6042,
    "day_of_week_encoding": 0.0
  },
  "clip_embedding": [0.123, -0.456, 0.789, ...],
  "semantic_scores": {
    "busy_intersection": 0.85,
    "quiet_street": 0.12,
    "rush_hour": 0.78
  },
  "model_metadata": {
    "yolov8n_version": "8.0.0",
    "detectron2_version": "0.6",
    "clip_model": "openai/clip-vit-base-patch32",
    "confidence_threshold": 0.25
  }
}
```

## Integration with Search Algorithm

The feature vector is designed to be embedded into the learned heuristic function:

```
h_learned(n) = w^T * f(zone(n))
```

Where:
- `f(zone(n))` extracts the feature vector for the camera zone containing intersection `n`
- `w` is a learned weight vector
- The feature vector components are normalized and scaled appropriately

### Feature Normalization

- **Count features**: Normalized by maximum expected values or log-transformed
- **Density features**: Already normalized to [0.0, 1.0] range
- **Temporal encodings**: Cyclic encodings for periodic patterns
- **Categorical features**: One-hot encoded or embedded

## Usage in Python

```python
from pax.schemas.feature_vector import FeatureVector, SpatialFeatures, VisualComplexityFeatures, TemporalFeatures
from datetime import datetime

# Create a feature vector
feature_vector = FeatureVector(
    spatial=SpatialFeatures(
        pedestrian_count=12,
        vehicle_count=8,
        bicycle_count=3,
        total_object_count=23,
        pedestrian_density=0.15,
        vehicle_density=0.08,
        crowd_density=0.65,
        object_density=0.23
    ),
    visual_complexity=VisualComplexityFeatures(
        scene_complexity=0.72,
        visual_noise=0.15,
        lighting_condition="daylight",
        lighting_brightness=0.85,
        weather_condition="clear",
        visibility_score=0.92,
        occlusion_score=0.18
    ),
    temporal=TemporalFeatures(
        timestamp=datetime(2025, 11, 10, 14, 30, 0),
        hour=14,
        minute=30,
        day_of_week=1,
        is_weekend=False,
        is_rush_hour=False,
        time_of_day_encoding=0.6042,
        day_of_week_encoding=0.0
    )
)

# Serialize to JSON
json_data = feature_vector.model_dump_json()

# Validate from dictionary
feature_vector = FeatureVector.model_validate(json_dict)
```

## Validation Rules

1. All count fields must be non-negative integers
2. All density and score fields must be in [0.0, 1.0] range (unless specified otherwise)
3. Temporal fields must be consistent (e.g., `hour` matches `timestamp.hour`)
4. `is_weekend` must be `True` when `day_of_week` is 6 or 7
5. `is_rush_hour` must be `True` when `hour` is 7-8 or 17-18 on weekdays
6. `clip_embedding` length must match model dimension (512 or 768)

## Related Documents

- [Vision Model Output Formats](../research/vision_model_outputs.md) - Details on model output structures
- [Multi-Agent Work Tree](../../agentHandoff/worktrees/MULTI_AGENT_WORK_TREE.md) - Task definitions

## Version History

- **v1.0** (2025-11-10): Initial schema definition with spatial, visual complexity, and temporal features

