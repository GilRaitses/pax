"""Feature vector schema for vision model outputs and empirical data structure."""

from __future__ import annotations

from datetime import datetime
from enum import IntEnum
from typing import Literal

from pydantic import BaseModel, Field


class DayOfWeek(IntEnum):
    """Day of week encoding (ISO 8601: Monday=1, Sunday=7)."""

    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6
    SUNDAY = 7


# Lighting and weather conditions are defined as Literal types in the model fields below


class SpatialFeatures(BaseModel):
    """Spatial features extracted from object detection models."""

    pedestrian_count: int = Field(
        ge=0,
        description="Number of detected pedestrians in the frame.",
    )
    vehicle_count: int = Field(
        ge=0,
        description="Number of detected vehicles (cars, trucks, buses, motorcycles) in the frame.",
    )
    bicycle_count: int = Field(
        ge=0,
        description="Number of detected bicycles in the frame.",
    )
    total_object_count: int = Field(
        ge=0,
        description="Total number of detected objects (all classes).",
    )
    pedestrian_density: float = Field(
        ge=0.0,
        description="Pedestrian density per square meter (estimated from detection area).",
    )
    vehicle_density: float = Field(
        ge=0.0,
        description="Vehicle density per square meter (estimated from detection area).",
    )
    crowd_density: float = Field(
        ge=0.0,
        le=1.0,
        description="Normalized crowd density metric (0.0 = empty, 1.0 = maximum density).",
    )
    object_density: float = Field(
        ge=0.0,
        description="Overall object density (objects per square meter).",
    )


class VisualComplexityFeatures(BaseModel):
    """Visual complexity features describing scene characteristics."""

    scene_complexity: float = Field(
        ge=0.0,
        le=1.0,
        description="Normalized scene complexity score (0.0 = simple, 1.0 = highly complex).",
    )
    visual_noise: float = Field(
        ge=0.0,
        le=1.0,
        description="Visual noise indicator (0.0 = clean, 1.0 = high noise).",
    )
    lighting_condition: Literal[
        "daylight", "twilight", "night", "artificial"
    ] = Field(
        description="Primary lighting condition in the scene.",
    )
    lighting_brightness: float = Field(
        ge=0.0,
        le=1.0,
        description="Normalized lighting brightness (0.0 = dark, 1.0 = bright).",
    )
    weather_condition: Literal[
        "clear", "cloudy", "rainy", "foggy", "snowy", "unknown"
    ] = Field(
        default="unknown",
        description="Weather condition inferred from visual analysis.",
    )
    visibility_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Normalized visibility metric (0.0 = poor visibility, 1.0 = excellent).",
    )
    occlusion_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Occlusion/obstruction score (0.0 = no occlusions, 1.0 = heavily occluded).",
    )


class TemporalFeatures(BaseModel):
    """Temporal features encoding time-based information."""

    timestamp: datetime = Field(
        description="Exact timestamp when the image was captured.",
    )
    hour: int = Field(
        ge=0,
        le=23,
        description="Hour of day (0-23) in local timezone.",
    )
    minute: int = Field(
        ge=0,
        le=59,
        description="Minute of hour (0-59).",
    )
    day_of_week: int = Field(
        ge=1,
        le=7,
        description="Day of week (1=Monday, 7=Sunday) per ISO 8601.",
    )
    is_weekend: bool = Field(
        description="Whether the day is a weekend (Saturday or Sunday).",
    )
    is_rush_hour: bool = Field(
        description="Whether the time falls within rush hour periods (7-9 AM or 5-7 PM).",
    )
    time_of_day_encoding: float = Field(
        ge=0.0,
        le=1.0,
        description="Normalized time of day encoding (0.0 = midnight, 1.0 = next midnight).",
    )
    day_of_week_encoding: float = Field(
        ge=0.0,
        le=1.0,
        description="Normalized day of week encoding (0.0 = Monday, 1.0 = Sunday).",
    )


class FeatureVector(BaseModel):
    """
    Comprehensive feature vector combining spatial, visual complexity, and temporal features.

    This schema represents the standardized empirical data structure for vision model outputs
    that can be embedded into the search algorithm for learned heuristic pathfinding.
    """

    # Spatial features from object detection (YOLOv8n, Detectron2)
    spatial: SpatialFeatures = Field(
        description="Spatial features describing object counts and densities.",
    )

    # Visual complexity features from scene analysis (Detectron2, CLIP)
    visual_complexity: VisualComplexityFeatures = Field(
        description="Visual complexity features describing scene characteristics.",
    )

    # Temporal features from image metadata
    temporal: TemporalFeatures = Field(
        description="Temporal features encoding time-based information.",
    )

    # Optional: CLIP semantic features (can be added later)
    clip_embedding: list[float] | None = Field(
        default=None,
        description="Optional CLIP image embedding vector (512 or 768 dimensions).",
    )
    semantic_scores: dict[str, float] | None = Field(
        default=None,
        description="Optional CLIP similarity scores for semantic prompts (e.g., 'busy intersection', 'quiet street').",
    )

    # Optional: Model metadata
    model_metadata: dict[str, str | float | int] | None = Field(
        default=None,
        description="Optional metadata about the vision models used (versions, confidence thresholds, etc.).",
    )

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

