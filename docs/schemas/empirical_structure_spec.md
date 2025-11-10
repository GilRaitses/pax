# Empirical Data Structure Specification

**Created:** November 10, 2025  
**Purpose:** Comprehensive specification for empirical data structure used in learned heuristic pathfinding

## Overview

This document defines the complete empirical data structure for vision model outputs that integrates with the A* search algorithm for learned heuristic pathfinding. The structure standardizes how perceptual and environmental features extracted from traffic camera images are represented and used to guide pathfinding decisions.

## Architecture

### Data Flow

```
Traffic Camera Images
    ↓
Vision Models (YOLOv8n, Detectron2, CLIP)
    ↓
Feature Extraction Pipeline
    ↓
FeatureVector (Empirical Data Structure)
    ↓
Voronoi Zone Mapping
    ↓
Intersection Feature Assignment
    ↓
Learned Heuristic Function
    ↓
A* Search Algorithm
```

### Zone-to-Intersection Mapping

Each intersection `n` inherits features from its nearest camera zone via Voronoi tessellation:

```
f(intersection) = f(zone(intersection))
```

Where `zone(intersection) = argmin_{c} d(intersection, c)` finds the nearest camera zone.

## Feature Vector Schema

The `FeatureVector` is the core empirical data structure, composed of three main feature groups:

### 1. Spatial Features

Spatial features capture object presence and density metrics from object detection models.

#### Feature Extraction

- **Source Models:** YOLOv8n (fast detection), Detectron2 (detailed segmentation)
- **Detection Classes:** Pedestrians, vehicles (cars, trucks, buses, motorcycles), bicycles
- **Density Calculation:** Based on bounding box areas and estimated scene dimensions

#### Fields

| Field | Type | Range | Description | Example |
|-------|------|-------|-------------|---------|
| `pedestrian_count` | `int` | ≥ 0 | Number of detected pedestrians | 12 |
| `vehicle_count` | `int` | ≥ 0 | Number of detected vehicles | 8 |
| `bicycle_count` | `int` | ≥ 0 | Number of detected bicycles | 3 |
| `total_object_count` | `int` | ≥ 0 | Total detected objects (all classes) | 23 |
| `pedestrian_density` | `float` | ≥ 0.0 | Pedestrians per square meter | 0.15 |
| `vehicle_density` | `float` | ≥ 0.0 | Vehicles per square meter | 0.08 |
| `crowd_density` | `float` | [0.0, 1.0] | Normalized crowd density | 0.65 |
| `object_density` | `float` | ≥ 0.0 | Objects per square meter | 0.23 |

#### Example: High Traffic Intersection

```python
spatial = SpatialFeatures(
    pedestrian_count=25,      # Busy crosswalk
    vehicle_count=15,         # Heavy traffic
    bicycle_count=5,          # Bike lane usage
    total_object_count=45,    # Total activity
    pedestrian_density=0.35,  # High pedestrian density
    vehicle_density=0.20,     # High vehicle density
    crowd_density=0.85,       # Very crowded
    object_density=0.45       # High overall density
)
```

#### Example: Quiet Residential Street

```python
spatial = SpatialFeatures(
    pedestrian_count=2,       # Few pedestrians
    vehicle_count=1,          # Minimal traffic
    bicycle_count=0,          # No bicycles
    total_object_count=3,     # Low activity
    pedestrian_density=0.02,   # Low density
    vehicle_density=0.01,      # Low density
    crowd_density=0.10,       # Not crowded
    object_density=0.03       # Low overall density
)
```

### 2. Visual Complexity Features

Visual complexity features describe scene characteristics, environmental conditions, and visual quality.

#### Feature Extraction

- **Source Models:** Detectron2 (segmentation masks), CLIP (semantic understanding)
- **Scene Analysis:** Complexity scores, noise detection, lighting classification
- **Environmental Inference:** Weather conditions, visibility assessment

#### Fields

| Field | Type | Range/Values | Description | Example |
|-------|------|--------------|-------------|---------|
| `scene_complexity` | `float` | [0.0, 1.0] | Normalized complexity score | 0.72 |
| `visual_noise` | `float` | [0.0, 1.0] | Visual noise indicator | 0.15 |
| `lighting_condition` | `str` | `"daylight"`, `"twilight"`, `"night"`, `"artificial"` | Primary lighting | `"daylight"` |
| `lighting_brightness` | `float` | [0.0, 1.0] | Normalized brightness | 0.85 |
| `weather_condition` | `str` | `"clear"`, `"cloudy"`, `"rainy"`, `"foggy"`, `"snowy"`, `"unknown"` | Weather type | `"clear"` |
| `visibility_score` | `float` | [0.0, 1.0] | Normalized visibility | 0.92 |
| `occlusion_score` | `float` | [0.0, 1.0] | Occlusion/obstruction score | 0.18 |

#### Example: Complex Urban Intersection

```python
visual_complexity = VisualComplexityFeatures(
    scene_complexity=0.85,      # Highly complex scene
    visual_noise=0.25,          # Some visual noise
    lighting_condition="daylight",
    lighting_brightness=0.90,   # Bright daylight
    weather_condition="clear",
    visibility_score=0.95,     # Excellent visibility
    occlusion_score=0.30        # Some occlusions
)
```

#### Example: Nighttime with Poor Visibility

```python
visual_complexity = VisualComplexityFeatures(
    scene_complexity=0.40,      # Less complex at night
    visual_noise=0.35,          # More noise in low light
    lighting_condition="night",
    lighting_brightness=0.15,   # Dark
    weather_condition="rainy",
    visibility_score=0.45,       # Poor visibility
    occlusion_score=0.20        # Moderate occlusions
)
```

### 3. Temporal Features

Temporal features encode time-based information and periodic patterns.

#### Feature Extraction

- **Source:** Image metadata (timestamp)
- **Encoding:** Normalized cyclic encodings for machine learning compatibility
- **Pattern Recognition:** Rush hour detection, weekend classification

#### Fields

| Field | Type | Range | Description | Example |
|-------|------|-------|-------------|---------|
| `timestamp` | `datetime` | - | Exact capture timestamp | `2025-11-10T14:30:00` |
| `hour` | `int` | [0, 23] | Hour of day | 14 |
| `minute` | `int` | [0, 59] | Minute of hour | 30 |
| `day_of_week` | `int` | [1, 7] | Day (1=Monday, 7=Sunday) | 1 |
| `is_weekend` | `bool` | - | Weekend flag | `False` |
| `is_rush_hour` | `bool` | - | Rush hour flag | `False` |
| `time_of_day_encoding` | `float` | [0.0, 1.0] | Normalized time encoding | 0.6042 |
| `day_of_week_encoding` | `float` | [0.0, 1.0] | Normalized day encoding | 0.0 |

#### Encoding Formulas

- **Time of Day:** `(hour * 60 + minute) / 1440.0`
- **Day of Week:** `(day_of_week - 1) / 7.0`
- **Rush Hour:** `hour in {7, 8, 17, 18} and day_of_week <= 5`
- **Weekend:** `day_of_week in {6, 7}`

#### Example: Rush Hour Weekday

```python
temporal = TemporalFeatures(
    timestamp=datetime(2025, 11, 10, 8, 15, 0),  # Monday 8:15 AM
    hour=8,
    minute=15,
    day_of_week=1,              # Monday
    is_weekend=False,
    is_rush_hour=True,          # Morning rush hour
    time_of_day_encoding=0.3438,  # 8:15 AM = 495 minutes / 1440
    day_of_week_encoding=0.0     # Monday = 0/7
)
```

#### Example: Weekend Afternoon

```python
temporal = TemporalFeatures(
    timestamp=datetime(2025, 11, 15, 15, 45, 0),  # Saturday 3:45 PM
    hour=15,
    minute=45,
    day_of_week=6,              # Saturday
    is_weekend=True,
    is_rush_hour=False,         # Not rush hour (weekend)
    time_of_day_encoding=0.6563,  # 3:45 PM = 945 minutes / 1440
    day_of_week_encoding=0.7143   # Saturday = 5/7
)
```

### 4. Optional Features

#### CLIP Embeddings

Semantic features from CLIP model for scene understanding:

```python
clip_embedding=[0.123, -0.456, 0.789, ...],  # 512 or 768 dimensions
semantic_scores={
    "busy_intersection": 0.85,
    "quiet_street": 0.12,
    "rush_hour": 0.78,
    "pedestrian_crossing": 0.65
}
```

#### Model Metadata

Information about vision models used:

```python
model_metadata={
    "yolov8n_version": "8.0.0",
    "detectron2_version": "0.6",
    "clip_model": "openai/clip-vit-base-patch32",
    "confidence_threshold": 0.25,
    "image_resolution": "1920x1080"
}
```

## Integration with Search Algorithm

### Learned Heuristic Function

The feature vector integrates into the learned heuristic function:

```
h_learned(n) = w^T * f(zone(n)) + b
```

Where:
- `f(zone(n))` extracts the feature vector for the camera zone containing intersection `n`
- `w` is a learned weight vector from Ridge regression
- `b` is the intercept term
- `zone(n) = argmin_{c} d(n, c)` finds the nearest camera zone

### Feature Vector Flattening

For machine learning integration, the feature vector is flattened into a numerical array:

```python
def flatten_feature_vector(fv: FeatureVector) -> list[float]:
    """Flatten feature vector for ML model input."""
    features = []
    
    # Spatial features (8 values)
    features.extend([
        fv.spatial.pedestrian_count,
        fv.spatial.vehicle_count,
        fv.spatial.bicycle_count,
        fv.spatial.total_object_count,
        fv.spatial.pedestrian_density,
        fv.spatial.vehicle_density,
        fv.spatial.crowd_density,
        fv.spatial.object_density,
    ])
    
    # Visual complexity features (7 values)
    features.extend([
        fv.visual_complexity.scene_complexity,
        fv.visual_complexity.visual_noise,
        # Lighting condition: one-hot encoded (4 values)
        1.0 if fv.visual_complexity.lighting_condition == "daylight" else 0.0,
        1.0 if fv.visual_complexity.lighting_condition == "twilight" else 0.0,
        1.0 if fv.visual_complexity.lighting_condition == "night" else 0.0,
        1.0 if fv.visual_complexity.lighting_condition == "artificial" else 0.0,
        fv.visual_complexity.lighting_brightness,
        # Weather condition: one-hot encoded (6 values)
        1.0 if fv.visual_complexity.weather_condition == "clear" else 0.0,
        1.0 if fv.visual_complexity.weather_condition == "cloudy" else 0.0,
        1.0 if fv.visual_complexity.weather_condition == "rainy" else 0.0,
        1.0 if fv.visual_complexity.weather_condition == "foggy" else 0.0,
        1.0 if fv.visual_complexity.weather_condition == "snowy" else 0.0,
        1.0 if fv.visual_complexity.weather_condition == "unknown" else 0.0,
        fv.visual_complexity.visibility_score,
        fv.visual_complexity.occlusion_score,
    ])
    
    # Temporal features (8 values)
    features.extend([
        fv.temporal.hour / 23.0,  # Normalize hour
        fv.temporal.minute / 59.0,  # Normalize minute
        fv.temporal.day_of_week / 7.0,  # Normalize day of week
        1.0 if fv.temporal.is_weekend else 0.0,
        1.0 if fv.temporal.is_rush_hour else 0.0,
        fv.temporal.time_of_day_encoding,
        fv.temporal.day_of_week_encoding,
        # Cyclic encoding for hour (sin/cos)
        math.sin(2 * math.pi * fv.temporal.hour / 24.0),
        math.cos(2 * math.pi * fv.temporal.hour / 24.0),
    ])
    
    # Optional: CLIP embedding (if present)
    if fv.clip_embedding:
        features.extend(fv.clip_embedding)
    
    return features
```

**Total Feature Dimensions:**
- Base features: 8 (spatial) + 7 (visual complexity) + 8 (temporal) = 23
- With one-hot encoding: ~35-40 features
- With CLIP embedding: ~555-800 features (depending on CLIP model)

### A* Search Integration

```python
def heuristic_function(intersection: Intersection, goal: Intersection) -> float:
    """Learned heuristic for A* search."""
    # Get feature vector for intersection's zone
    zone = find_nearest_zone(intersection)
    feature_vector = get_zone_features(zone)
    
    # Flatten feature vector
    features = flatten_feature_vector(feature_vector)
    
    # Compute learned heuristic
    h_learned = learned_model.predict(features)
    
    # Combine with Manhattan distance (admissible baseline)
    h_manhattan = manhattan_distance(intersection, goal)
    
    # Weighted combination
    return alpha * h_learned + (1 - alpha) * h_manhattan
```

## Usage Examples

### Creating a Feature Vector

```python
from pax.schemas.feature_vector import FeatureVector, SpatialFeatures, VisualComplexityFeatures, TemporalFeatures
from datetime import datetime

# Create feature vector from vision model outputs
feature_vector = FeatureVector(
    spatial=SpatialFeatures(
        pedestrian_count=12,
        vehicle_count=8,
        bicycle_count=3,
        total_object_count=23,
        pedestrian_density=0.15,
        vehicle_density=0.08,
        crowd_density=0.65,
        object_density=0.23,
    ),
    visual_complexity=VisualComplexityFeatures(
        scene_complexity=0.72,
        visual_noise=0.15,
        lighting_condition="daylight",
        lighting_brightness=0.85,
        weather_condition="clear",
        visibility_score=0.92,
        occlusion_score=0.18,
    ),
    temporal=TemporalFeatures(
        timestamp=datetime(2025, 11, 10, 14, 30, 0),
        hour=14,
        minute=30,
        day_of_week=1,
        is_weekend=False,
        is_rush_hour=False,
        time_of_day_encoding=0.6042,
        day_of_week_encoding=0.0,
    ),
    clip_embedding=[0.123, -0.456, ...],  # Optional
    semantic_scores={"busy_intersection": 0.85},  # Optional
)
```

### Validating a Feature Vector

```python
from pax.schemas.validation import validate_feature_vector, ValidationResult

# Validate feature vector
result: ValidationResult = validate_feature_vector(feature_vector)

if result.is_valid:
    print("Feature vector is valid")
else:
    print(f"Validation errors: {result.errors}")
    print(f"Warnings: {result.warnings}")
```

### Handling Missing Values

```python
from pax.schemas.validation import handle_missing_values

# Incomplete data from vision pipeline
incomplete_data = {
    "spatial": {"pedestrian_count": 5},  # Missing other fields
    "temporal": {...},  # Complete temporal data
}

# Fill missing values with defaults
complete_data = handle_missing_values(incomplete_data)

# Now can create FeatureVector
feature_vector = FeatureVector.model_validate(complete_data)
```

### Zone-to-Intersection Mapping

```python
from pax.voronoi.generator import VoronoiZones
from pax.schemas.feature_vector import FeatureVector

# Load Voronoi zones
zones = VoronoiZones.load("data/geojson/voronoi_zones.geojson")

# Get feature vector for an intersection
intersection_point = (40.7589, -73.9851)  # Times Square
zone = zones.find_nearest_zone(intersection_point)
feature_vector = get_zone_features(zone)  # From database/storage

# Use in heuristic
h_value = learned_heuristic(feature_vector)
```

## Best Practices

### 1. Feature Extraction

- **Consistency:** Always use the same vision models and confidence thresholds
- **Normalization:** Ensure density metrics are calculated consistently
- **Temporal Accuracy:** Use precise timestamps and validate temporal consistency

### 2. Data Validation

- **Always Validate:** Use `validate_feature_vector()` before storing or using features
- **Handle Missing Values:** Use `handle_missing_values()` for incomplete data
- **Check Consistency:** Review warnings for cross-field inconsistencies

### 3. Storage

- **Format:** Store as JSON for interoperability
- **Versioning:** Include model metadata for reproducibility
- **Indexing:** Index by camera_id and timestamp for efficient retrieval

### 4. Integration

- **Feature Normalization:** Normalize features before ML model input
- **Zone Mapping:** Cache zone-to-intersection mappings for performance
- **Heuristic Combination:** Balance learned heuristic with admissible baseline

## Edge Cases

### Very Busy Zone

```python
# High stress intersection during rush hour
FeatureVector(
    spatial=SpatialFeatures(
        pedestrian_count=50,      # Very high
        vehicle_count=30,         # Heavy traffic
        crowd_density=0.95,      # Maximum density
        ...
    ),
    temporal=TemporalFeatures(
        is_rush_hour=True,       # Rush hour
        ...
    ),
)
```

### Very Quiet Zone

```python
# Low stress residential area
FeatureVector(
    spatial=SpatialFeatures(
        pedestrian_count=1,       # Minimal activity
        vehicle_count=0,          # No traffic
        crowd_density=0.05,      # Very low density
        ...
    ),
    temporal=TemporalFeatures(
        is_weekend=True,         # Weekend
        is_rush_hour=False,     # Off-peak
        ...
    ),
)
```

### Poor Visibility Conditions

```python
# Nighttime with bad weather
FeatureVector(
    visual_complexity=VisualComplexityFeatures(
        lighting_condition="night",
        lighting_brightness=0.10,  # Very dark
        weather_condition="rainy",
        visibility_score=0.30,      # Poor visibility
        ...
    ),
)
```

## Related Documents

- [Feature Vector Schema Specification](./feature_vector_spec.md) - Detailed schema reference
- [Vision Model Output Formats](../research/vision_model_outputs.md) - Model output structures
- [Multi-Agent Work Tree](../../agentHandoff/worktrees/MULTI_AGENT_WORK_TREE.md) - Task definitions
- [Validation Module](../../../src/pax/schemas/validation.py) - Validation functions

## Version History

- **v1.0** (2025-11-10): Initial specification with spatial, visual complexity, and temporal features

