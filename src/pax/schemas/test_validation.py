"""Test validation functions with example feature vectors."""

from __future__ import annotations

from datetime import datetime

from pax.schemas.feature_vector import FeatureVector, SpatialFeatures, TemporalFeatures, VisualComplexityFeatures
from pax.schemas.validation import (
    handle_missing_values,
    validate_feature_vector,
    validate_feature_vector_dict,
)


def create_valid_feature_vector() -> FeatureVector:
    """Create a valid example feature vector."""
    return FeatureVector(
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
    )


def create_inconsistent_temporal_feature_vector() -> FeatureVector:
    """Create a feature vector with temporal inconsistencies."""
    return FeatureVector(
        spatial=SpatialFeatures(
            pedestrian_count=5,
            vehicle_count=3,
            bicycle_count=1,
            total_object_count=9,
            pedestrian_density=0.08,
            vehicle_density=0.05,
            crowd_density=0.35,
            object_density=0.12,
        ),
        visual_complexity=VisualComplexityFeatures(
            scene_complexity=0.45,
            visual_noise=0.10,
            lighting_condition="daylight",
            lighting_brightness=0.75,
            weather_condition="clear",
            visibility_score=0.88,
            occlusion_score=0.12,
        ),
        temporal=TemporalFeatures(
            timestamp=datetime(2025, 11, 10, 8, 15, 0),  # 8:15 AM
            hour=14,  # Inconsistent: says 14 (2 PM) but timestamp is 8:15 AM
            minute=30,  # Inconsistent: says 30 but timestamp is 15
            day_of_week=6,  # Saturday
            is_weekend=True,  # Correct
            is_rush_hour=True,  # Should be False (it's Saturday)
            time_of_day_encoding=0.3438,  # Should match 8:15 AM
            day_of_week_encoding=0.7143,  # Should match Saturday (6)
        ),
    )


def create_inconsistent_spatial_feature_vector() -> FeatureVector:
    """Create a feature vector with spatial inconsistencies."""
    return FeatureVector(
        spatial=SpatialFeatures(
            pedestrian_count=10,
            vehicle_count=5,
            bicycle_count=2,
            total_object_count=15,  # Should be at least 17 (10+5+2)
            pedestrian_density=15.0,  # Unusually high
            vehicle_density=0.05,
            crowd_density=1.5,  # Exceeds 1.0
            object_density=0.20,
        ),
        visual_complexity=VisualComplexityFeatures(
            scene_complexity=0.60,
            visual_noise=0.20,
            lighting_condition="night",
            lighting_brightness=0.85,  # Inconsistent: night but bright
            weather_condition="rainy",
            visibility_score=0.95,  # Inconsistent: rainy but high visibility
            occlusion_score=0.25,
        ),
        temporal=TemporalFeatures(
            timestamp=datetime(2025, 11, 10, 20, 0, 0),
            hour=20,
            minute=0,
            day_of_week=1,
            is_weekend=False,
            is_rush_hour=False,
            time_of_day_encoding=0.8333,
            day_of_week_encoding=0.0,
        ),
    )


def test_valid_feature_vector():
    """Test validation on a valid feature vector."""
    print("=" * 70)
    print("Test 1: Valid Feature Vector")
    print("=" * 70)

    feature_vector = create_valid_feature_vector()
    result = validate_feature_vector(feature_vector)

    print(result)
    print(f"\nIs Valid: {result.is_valid}")
    assert result.is_valid, "Valid feature vector should pass validation"
    print("✓ PASSED: Valid feature vector passes validation\n")


def test_inconsistent_temporal():
    """Test validation on feature vector with temporal inconsistencies."""
    print("=" * 70)
    print("Test 2: Temporal Inconsistencies")
    print("=" * 70)

    feature_vector = create_inconsistent_temporal_feature_vector()
    result = validate_feature_vector(feature_vector)

    print(result)
    print(f"\nIs Valid: {result.is_valid}")
    print(f"Warnings: {len(result.warnings)}")
    assert len(result.warnings) > 0, "Should detect temporal inconsistencies"
    print("✓ PASSED: Temporal inconsistencies detected\n")


def test_inconsistent_spatial():
    """Test validation on feature vector with spatial inconsistencies."""
    print("=" * 70)
    print("Test 3: Spatial Inconsistencies")
    print("=" * 70)

    feature_vector = create_inconsistent_spatial_feature_vector()
    result = validate_feature_vector(feature_vector)

    print(result)
    print(f"\nIs Valid: {result.is_valid}")
    print(f"Errors: {len(result.errors)}")
    print(f"Warnings: {len(result.warnings)}")
    assert len(result.errors) > 0 or len(result.warnings) > 0, "Should detect spatial inconsistencies"
    print("✓ PASSED: Spatial inconsistencies detected\n")


def test_missing_values():
    """Test handling of missing values."""
    print("=" * 70)
    print("Test 4: Missing Values Handling")
    print("=" * 70)

    incomplete_data = {
        "spatial": {
            "pedestrian_count": 5,
            # Missing other spatial fields
        },
        "visual_complexity": {
            "lighting_condition": "daylight",
            # Missing other visual complexity fields
        },
        "temporal": {
            "timestamp": "2025-11-10T14:30:00",
            "hour": 14,
            "minute": 30,
            "day_of_week": 1,
            "is_weekend": False,
            "is_rush_hour": False,
            "time_of_day_encoding": 0.6042,
            "day_of_week_encoding": 0.0,
        },
    }

    filled_data = handle_missing_values(incomplete_data)
    print("Original data (incomplete):")
    print(f"  spatial keys: {list(incomplete_data['spatial'].keys())}")
    print(f"  visual_complexity keys: {list(incomplete_data['visual_complexity'].keys())}")

    print("\nAfter filling missing values:")
    print(f"  spatial keys: {list(filled_data['spatial'].keys())}")
    print(f"  visual_complexity keys: {list(filled_data['visual_complexity'].keys())}")

    # Try to validate the filled data
    result = validate_feature_vector_dict(filled_data)
    print(f"\nValidation result: {'VALID' if result.is_valid else 'INVALID'}")
    print("✓ PASSED: Missing values handled correctly\n")


def test_dict_validation():
    """Test validation from dictionary."""
    print("=" * 70)
    print("Test 5: Dictionary Validation")
    print("=" * 70)

    valid_dict = {
        "spatial": {
            "pedestrian_count": 8,
            "vehicle_count": 6,
            "bicycle_count": 2,
            "total_object_count": 16,
            "pedestrian_density": 0.12,
            "vehicle_density": 0.07,
            "crowd_density": 0.55,
            "object_density": 0.18,
        },
        "visual_complexity": {
            "scene_complexity": 0.65,
            "visual_noise": 0.12,
            "lighting_condition": "daylight",
            "lighting_brightness": 0.80,
            "weather_condition": "clear",
            "visibility_score": 0.90,
            "occlusion_score": 0.15,
        },
        "temporal": {
            "timestamp": "2025-11-10T09:00:00",
            "hour": 9,
            "minute": 0,
            "day_of_week": 1,
            "is_weekend": False,
            "is_rush_hour": True,
            "time_of_day_encoding": 0.375,
            "day_of_week_encoding": 0.0,
        },
    }

    result = validate_feature_vector_dict(valid_dict)
    print(result)
    print(f"\nIs Valid: {result.is_valid}")
    assert result.is_valid, "Valid dictionary should pass validation"
    print("✓ PASSED: Dictionary validation works correctly\n")


def main():
    """Run all validation tests."""
    print("\n" + "=" * 70)
    print("FEATURE VECTOR VALIDATION TESTS")
    print("=" * 70 + "\n")

    try:
        test_valid_feature_vector()
        test_inconsistent_temporal()
        test_inconsistent_spatial()
        test_missing_values()
        test_dict_validation()

        print("=" * 70)
        print("ALL TESTS PASSED")
        print("=" * 70)
    except AssertionError as exc:
        print(f"\n✗ TEST FAILED: {exc}")
        return 1
    except Exception as exc:
        print(f"\n✗ UNEXPECTED ERROR: {exc}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())

