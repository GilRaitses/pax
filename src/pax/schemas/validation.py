"""Validation functions for feature vectors and empirical data structures."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from pydantic import ValidationError

from pax.schemas.feature_vector import FeatureVector, SpatialFeatures, TemporalFeatures, VisualComplexityFeatures

LOGGER = logging.getLogger(__name__)


class ValidationWarning:
    """Represents a validation warning (non-fatal issue)."""

    def __init__(self, field: str, message: str, severity: str = "warning"):
        self.field = field
        self.message = message
        self.severity = severity

    def __str__(self) -> str:
        return f"{self.severity.upper()}: {self.field}: {self.message}"

    def __repr__(self) -> str:
        return f"ValidationWarning(field={self.field!r}, message={self.message!r}, severity={self.severity!r})"


class ValidationResult:
    """Result of feature vector validation."""

    def __init__(self, is_valid: bool, errors: list[str] | None = None, warnings: list[ValidationWarning] | None = None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []

    def __bool__(self) -> bool:
        return self.is_valid

    def __str__(self) -> str:
        status = "VALID" if self.is_valid else "INVALID"
        result = [f"Validation Status: {status}"]
        if self.errors:
            result.append(f"Errors ({len(self.errors)}):")
            result.extend(f"  - {err}" for err in self.errors)
        if self.warnings:
            result.append(f"Warnings ({len(self.warnings)}):")
            result.extend(f"  - {warn}" for warn in self.warnings)
        return "\n".join(result)


def validate_temporal_consistency(temporal: TemporalFeatures) -> list[ValidationWarning]:
    """
    Validate temporal feature consistency.

    Checks:
    - hour/minute match timestamp
    - day_of_week matches timestamp
    - is_weekend matches day_of_week
    - is_rush_hour matches hour and day_of_week
    - time encodings are correct

    Args:
        temporal: Temporal features to validate

    Returns:
        List of validation warnings
    """
    warnings = []

    # Check hour/minute consistency
    if temporal.timestamp.hour != temporal.hour:
        warnings.append(
            ValidationWarning(
                "temporal.hour",
                f"Hour mismatch: timestamp has {temporal.timestamp.hour}, but hour field is {temporal.hour}",
            )
        )
    if temporal.timestamp.minute != temporal.minute:
        warnings.append(
            ValidationWarning(
                "temporal.minute",
                f"Minute mismatch: timestamp has {temporal.timestamp.minute}, but minute field is {temporal.minute}",
            )
        )

    # Check day of week consistency (ISO 8601: Monday=1)
    timestamp_dow = temporal.timestamp.isoweekday()
    if timestamp_dow != temporal.day_of_week:
        warnings.append(
            ValidationWarning(
                "temporal.day_of_week",
                f"Day of week mismatch: timestamp has {timestamp_dow}, but day_of_week field is {temporal.day_of_week}",
            )
        )

    # Check is_weekend consistency
    expected_weekend = temporal.day_of_week in {6, 7}  # Saturday or Sunday
    if temporal.is_weekend != expected_weekend:
        warnings.append(
            ValidationWarning(
                "temporal.is_weekend",
                f"is_weekend mismatch: day_of_week={temporal.day_of_week} implies is_weekend={expected_weekend}, but got {temporal.is_weekend}",
            )
        )

    # Check is_rush_hour consistency
    # Rush hour: 7-9 AM (7, 8) or 5-7 PM (17, 18) on weekdays
    expected_rush_hour = False
    if temporal.day_of_week <= 5:  # Weekday
        if temporal.hour in {7, 8, 17, 18}:
            expected_rush_hour = True
    if temporal.is_rush_hour != expected_rush_hour:
        warnings.append(
            ValidationWarning(
                "temporal.is_rush_hour",
                f"is_rush_hour mismatch: hour={temporal.hour}, day_of_week={temporal.day_of_week} implies is_rush_hour={expected_rush_hour}, but got {temporal.is_rush_hour}",
            )
        )

    # Check time encodings
    expected_time_encoding = (temporal.hour * 60 + temporal.minute) / 1440.0
    if abs(temporal.time_of_day_encoding - expected_time_encoding) > 0.001:
        warnings.append(
            ValidationWarning(
                "temporal.time_of_day_encoding",
                f"Time encoding mismatch: expected {expected_time_encoding:.4f}, got {temporal.time_of_day_encoding:.4f}",
            )
        )

    expected_dow_encoding = (temporal.day_of_week - 1) / 7.0
    if abs(temporal.day_of_week_encoding - expected_dow_encoding) > 0.001:
        warnings.append(
            ValidationWarning(
                "temporal.day_of_week_encoding",
                f"Day of week encoding mismatch: expected {expected_dow_encoding:.4f}, got {temporal.day_of_week_encoding:.4f}",
            )
        )

    return warnings


def validate_spatial_consistency(spatial: SpatialFeatures) -> list[ValidationWarning]:
    """
    Validate spatial feature consistency.

    Checks:
    - total_object_count matches sum of individual counts
    - Density values are reasonable
    - Counts are non-negative

    Args:
        spatial: Spatial features to validate

    Returns:
        List of validation warnings
    """
    warnings = []

    # Check total count consistency
    expected_total = spatial.pedestrian_count + spatial.vehicle_count + spatial.bicycle_count
    # Note: total_object_count may include other classes, so we check if it's at least the sum
    if spatial.total_object_count < expected_total:
        warnings.append(
            ValidationWarning(
                "spatial.total_object_count",
                f"total_object_count ({spatial.total_object_count}) is less than sum of pedestrian+vehicle+bicycle ({expected_total})",
                severity="error",
            )
        )

    # Check density reasonableness (warn if extremely high)
    if spatial.pedestrian_density > 10.0:
        warnings.append(
            ValidationWarning(
                "spatial.pedestrian_density",
                f"Unusually high pedestrian density: {spatial.pedestrian_density:.2f} pedestrians/m²",
            )
        )
    if spatial.vehicle_density > 5.0:
        warnings.append(
            ValidationWarning(
                "spatial.vehicle_density",
                f"Unusually high vehicle density: {spatial.vehicle_density:.2f} vehicles/m²",
            )
        )

    # Check crowd_density is normalized
    if spatial.crowd_density > 1.0:
        warnings.append(
            ValidationWarning(
                "spatial.crowd_density",
                f"crowd_density exceeds 1.0: {spatial.crowd_density:.4f}",
                severity="error",
            )
        )

    return warnings


def validate_visual_complexity_consistency(visual: VisualComplexityFeatures) -> list[ValidationWarning]:
    """
    Validate visual complexity feature consistency.

    Checks:
    - Score ranges are valid
    - Lighting condition matches brightness
    - Weather condition is reasonable

    Args:
        visual: Visual complexity features to validate

    Returns:
        List of validation warnings
    """
    warnings = []

    # Check lighting condition matches brightness
    if visual.lighting_condition == "night" and visual.lighting_brightness > 0.3:
        warnings.append(
            ValidationWarning(
                "visual_complexity.lighting_brightness",
                f"Night lighting condition but brightness is {visual.lighting_brightness:.2f} (expected < 0.3)",
            )
        )
    if visual.lighting_condition == "daylight" and visual.lighting_brightness < 0.5:
        warnings.append(
            ValidationWarning(
                "visual_complexity.lighting_brightness",
                f"Daylight condition but brightness is {visual.lighting_brightness:.2f} (expected > 0.5)",
            )
        )

    # Check visibility vs weather
    if visual.weather_condition in {"rainy", "foggy", "snowy"} and visual.visibility_score > 0.8:
        warnings.append(
            ValidationWarning(
                "visual_complexity.visibility_score",
                f"Weather is {visual.weather_condition} but visibility score is {visual.visibility_score:.2f} (expected lower)",
            )
        )

    # Check score ranges
    if visual.scene_complexity > 1.0 or visual.scene_complexity < 0.0:
        warnings.append(
            ValidationWarning(
                "visual_complexity.scene_complexity",
                f"scene_complexity out of range [0.0, 1.0]: {visual.scene_complexity:.4f}",
                severity="error",
            )
        )

    return warnings


def validate_clip_embedding(clip_embedding: list[float] | None) -> list[ValidationWarning]:
    """
    Validate CLIP embedding format.

    Checks:
    - Embedding dimension is valid (512 or 768)
    - Values are reasonable (not NaN, not infinite)

    Args:
        clip_embedding: CLIP embedding vector or None

    Returns:
        List of validation warnings
    """
    warnings = []

    if clip_embedding is None:
        return warnings

    dim = len(clip_embedding)
    if dim not in {512, 768}:
        warnings.append(
            ValidationWarning(
                "clip_embedding",
                f"CLIP embedding dimension is {dim}, expected 512 or 768",
                severity="error",
            )
        )

    # Check for NaN or infinite values
    for i, val in enumerate(clip_embedding):
        if not isinstance(val, (int, float)):
            warnings.append(
                ValidationWarning(
                    "clip_embedding",
                    f"Non-numeric value at index {i}: {val}",
                    severity="error",
                )
            )
        elif not (-10.0 <= val <= 10.0):  # CLIP embeddings are typically normalized
            warnings.append(
                ValidationWarning(
                    "clip_embedding",
                    f"Unusual embedding value at index {i}: {val}",
                )
            )

    return warnings


def validate_feature_vector(feature_vector: FeatureVector, strict: bool = False) -> ValidationResult:
    """
    Validate a feature vector comprehensively.

    Performs:
    1. Pydantic schema validation (basic types and ranges)
    2. Cross-field consistency checks
    3. Business logic validation

    Args:
        feature_vector: Feature vector to validate
        strict: If True, treat warnings as errors

    Returns:
        ValidationResult with validation status, errors, and warnings
    """
    errors = []
    warnings = []

    # Pydantic validation is already done when creating the model
    # But we can catch any validation errors if constructing from dict
    try:
        # Validate temporal consistency
        warnings.extend(validate_temporal_consistency(feature_vector.temporal))

        # Validate spatial consistency
        warnings.extend(validate_spatial_consistency(feature_vector.spatial))

        # Validate visual complexity consistency
        warnings.extend(validate_visual_complexity_consistency(feature_vector.visual_complexity))

        # Validate CLIP embedding if present
        if feature_vector.clip_embedding is not None:
            warnings.extend(validate_clip_embedding(feature_vector.clip_embedding))

        # Validate semantic scores if present
        if feature_vector.semantic_scores is not None:
            for key, score in feature_vector.semantic_scores.items():
                if not isinstance(score, (int, float)):
                    errors.append(f"semantic_scores['{key}'] must be numeric, got {type(score).__name__}")
                elif not (-1.0 <= score <= 1.0):
                    warnings.append(
                        ValidationWarning(
                            f"semantic_scores['{key}']",
                            f"Semantic score out of typical range [-1.0, 1.0]: {score:.4f}",
                        )
                    )

    except Exception as exc:
        errors.append(f"Validation error: {exc}")

    # Convert warnings to errors if strict mode
    if strict:
        errors.extend(str(w) for w in warnings if w.severity == "error")
        errors.extend(str(w) for w in warnings)  # All warnings become errors in strict mode
        warnings = []

    # Separate errors from warnings
    error_warnings = [w for w in warnings if w.severity == "error"]
    non_error_warnings = [w for w in warnings if w.severity != "error"]
    errors.extend(str(w) for w in error_warnings)

    is_valid = len(errors) == 0

    return ValidationResult(is_valid=is_valid, errors=errors, warnings=non_error_warnings)


def validate_feature_vector_dict(data: dict[str, Any], strict: bool = False) -> ValidationResult:
    """
    Validate a feature vector from a dictionary.

    First attempts to construct a FeatureVector from the dict (Pydantic validation),
    then performs additional consistency checks.

    Args:
        data: Dictionary containing feature vector data
        strict: If True, treat warnings as errors

    Returns:
        ValidationResult with validation status, errors, and warnings
    """
    errors = []
    warnings = []

    # Try to construct FeatureVector (Pydantic validation)
    try:
        feature_vector = FeatureVector.model_validate(data)
    except ValidationError as exc:
        errors.append(f"Schema validation failed: {exc}")
        return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

    # Perform additional validation
    result = validate_feature_vector(feature_vector, strict=strict)
    return result


def handle_missing_values(data: dict[str, Any], defaults: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Handle missing values in feature vector data with sensible defaults.

    Args:
        data: Dictionary containing feature vector data (may have missing fields)
        defaults: Optional dictionary of default values to use

    Returns:
        Dictionary with missing values filled in
    """
    if defaults is None:
        defaults = {
            "spatial": {
                "pedestrian_count": 0,
                "vehicle_count": 0,
                "bicycle_count": 0,
                "total_object_count": 0,
                "pedestrian_density": 0.0,
                "vehicle_density": 0.0,
                "crowd_density": 0.0,
                "object_density": 0.0,
            },
            "visual_complexity": {
                "scene_complexity": 0.0,
                "visual_noise": 0.0,
                "lighting_condition": "unknown",
                "lighting_brightness": 0.5,
                "weather_condition": "unknown",
                "visibility_score": 1.0,
                "occlusion_score": 0.0,
            },
        }

    result = data.copy()

    # Fill in missing spatial features
    if "spatial" not in result:
        result["spatial"] = defaults.get("spatial", {})
    else:
        for key, default_value in defaults.get("spatial", {}).items():
            if key not in result["spatial"]:
                result["spatial"][key] = default_value

    # Fill in missing visual complexity features
    if "visual_complexity" not in result:
        result["visual_complexity"] = defaults.get("visual_complexity", {})
    else:
        for key, default_value in defaults.get("visual_complexity", {}).items():
            if key not in result["visual_complexity"]:
                result["visual_complexity"][key] = default_value

    # Temporal features are required, but we can provide defaults if missing
    if "temporal" not in result:
        # Use current time as default
        now = datetime.now()
        result["temporal"] = {
            "timestamp": now.isoformat(),
            "hour": now.hour,
            "minute": now.minute,
            "day_of_week": now.isoweekday(),
            "is_weekend": now.isoweekday() in {6, 7},
            "is_rush_hour": (
                now.isoweekday() <= 5 and now.hour in {7, 8, 17, 18}
            ),
            "time_of_day_encoding": (now.hour * 60 + now.minute) / 1440.0,
            "day_of_week_encoding": (now.isoweekday() - 1) / 7.0,
        }

    return result

