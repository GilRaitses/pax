#!/usr/bin/env python3
"""Data quality checks for feature vectors.

This script validates feature completeness, checks for outliers,
and identifies data quality issues using BRANCH 2's validation functions.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from pax.schemas.feature_vector import FeatureVector
from pax.schemas.validation import ValidationResult, validate_feature_vector_dict
from pax.storage.feature_query import FeatureQuery

LOGGER = logging.getLogger(__name__)


def check_feature_completeness(df: pd.DataFrame) -> dict[str, Any]:
    """Check feature completeness (missing values, required fields)."""
    completeness = {
        "total_rows": len(df),
        "missing_values": {},
        "required_fields": [
            "spatial_pedestrian_count",
            "spatial_vehicle_count",
            "spatial_bicycle_count",
            "spatial_crowd_density",
            "visual_scene_complexity",
            "visual_visibility_score",
            "temporal_timestamp",
            "temporal_hour",
        ],
    }

    # Check for missing values in required fields
    for field in completeness["required_fields"]:
        if field in df.columns:
            missing_count = df[field].isna().sum()
            completeness["missing_values"][field] = {
                "count": int(missing_count),
                "percentage": float(missing_count / len(df) * 100) if len(df) > 0 else 0,
            }
        else:
            completeness["missing_values"][field] = {
                "count": len(df),
                "percentage": 100.0,
                "status": "FIELD_MISSING",
            }

    # Calculate overall completeness score
    total_fields = len(completeness["required_fields"])
    complete_fields = sum(
        1
        for field in completeness["required_fields"]
        if field in df.columns and completeness["missing_values"][field]["count"] == 0
    )
    completeness["completeness_score"] = float(complete_fields / total_fields * 100) if total_fields > 0 else 0

    return completeness


def check_outliers(df: pd.DataFrame) -> dict[str, Any]:
    """Check for outliers in numeric fields."""
    outlier_report = {
        "outliers": {},
        "statistics": {},
    }

    numeric_fields = [
        "spatial_pedestrian_count",
        "spatial_vehicle_count",
        "spatial_bicycle_count",
        "spatial_crowd_density",
        "visual_scene_complexity",
        "visual_visibility_score",
    ]

    for field in numeric_fields:
        if field not in df.columns:
            continue

        series = df[field].dropna()
        if len(series) == 0:
            continue

        # Calculate statistics
        mean = float(series.mean())
        std = float(series.std())
        q1 = float(series.quantile(0.25))
        q3 = float(series.quantile(0.75))
        iqr = q3 - q1

        outlier_report["statistics"][field] = {
            "mean": mean,
            "std": std,
            "min": float(series.min()),
            "max": float(series.max()),
            "q1": q1,
            "q3": q3,
            "iqr": iqr,
        }

        # Identify outliers using IQR method
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        outliers = series[(series < lower_bound) | (series > upper_bound)]

        outlier_report["outliers"][field] = {
            "count": len(outliers),
            "percentage": float(len(outliers) / len(series) * 100) if len(series) > 0 else 0,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "outlier_values": outliers.tolist()[:10],  # Limit to first 10
        }

    return outlier_report


def validate_feature_vectors(df: pd.DataFrame, strict: bool = False) -> dict[str, Any]:
    """Validate feature vectors using BRANCH 2's validation functions."""
    validation_results = {
        "total_validated": 0,
        "valid_count": 0,
        "invalid_count": 0,
        "error_summary": {},
        "warning_summary": {},
        "sample_errors": [],
        "sample_warnings": [],
    }

    # Convert DataFrame rows back to feature vector dictionaries
    for idx, row in df.iterrows():
        try:
            # Convert flattened row to feature vector dict format
            fv_dict = {
                "spatial": {
                    "pedestrian_count": int(row.get("spatial_pedestrian_count", 0)),
                    "vehicle_count": int(row.get("spatial_vehicle_count", 0)),
                    "bicycle_count": int(row.get("spatial_bicycle_count", 0)),
                    "total_object_count": int(row.get("spatial_total_object_count", 0)),
                    "pedestrian_density": float(row.get("spatial_pedestrian_density", 0.0)),
                    "vehicle_density": float(row.get("spatial_vehicle_density", 0.0)),
                    "crowd_density": float(row.get("spatial_crowd_density", 0.0)),
                    "object_density": float(row.get("spatial_object_density", 0.0)),
                },
                "visual_complexity": {
                    "scene_complexity": float(row.get("visual_scene_complexity", 0.0)),
                    "visual_noise": float(row.get("visual_noise", 0.0)),
                    "lighting_condition": row.get("visual_lighting_condition", "unknown"),
                    "lighting_brightness": float(row.get("visual_lighting_brightness", 0.5)),
                    "weather_condition": row.get("visual_weather_condition", "unknown"),
                    "visibility_score": float(row.get("visual_visibility_score", 1.0)),
                    "occlusion_score": float(row.get("visual_occlusion_score", 0.0)),
                },
                "temporal": {
                    "timestamp": pd.to_datetime(row.get("temporal_timestamp")).isoformat(),
                    "hour": int(row.get("temporal_hour", 0)),
                    "minute": int(row.get("temporal_minute", 0)),
                    "day_of_week": int(row.get("temporal_day_of_week", 1)),
                    "is_weekend": bool(row.get("temporal_is_weekend", False)),
                    "is_rush_hour": bool(row.get("temporal_is_rush_hour", False)),
                    "time_of_day_encoding": float(row.get("temporal_time_of_day_encoding", 0.0)),
                    "day_of_week_encoding": float(row.get("temporal_day_of_week_encoding", 0.0)),
                },
            }

            # Optional fields
            if pd.notna(row.get("clip_embedding")):
                import json

                fv_dict["clip_embedding"] = json.loads(row["clip_embedding"])

            # Validate
            result = validate_feature_vector_dict(fv_dict, strict=strict)
            validation_results["total_validated"] += 1

            if result.is_valid:
                validation_results["valid_count"] += 1
            else:
                validation_results["invalid_count"] += 1
                if len(validation_results["sample_errors"]) < 10:
                    validation_results["sample_errors"].append(
                        {
                            "index": int(idx),
                            "image_path": row.get("image_path", "unknown"),
                            "errors": result.errors[:3],  # First 3 errors
                        }
                    )

            # Collect warnings
            if result.warnings:
                for warning in result.warnings:
                    field = warning.field if hasattr(warning, "field") else "unknown"
                    if field not in validation_results["warning_summary"]:
                        validation_results["warning_summary"][field] = 0
                    validation_results["warning_summary"][field] += 1

                    if len(validation_results["sample_warnings"]) < 10:
                        validation_results["sample_warnings"].append(
                            {
                                "index": int(idx),
                                "image_path": row.get("image_path", "unknown"),
                                "warning": str(warning),
                            }
                        )

        except Exception as e:
            validation_results["invalid_count"] += 1
            if "validation_error" not in validation_results["error_summary"]:
                validation_results["error_summary"]["validation_error"] = 0
            validation_results["error_summary"]["validation_error"] += 1
            LOGGER.warning("Validation failed for row %d: %s", idx, e)

    return validation_results


def generate_quality_report(features_dir: Path, strict: bool = False) -> dict[str, Any]:
    """Generate comprehensive data quality report."""
    query = FeatureQuery(features_dir)
    parquet_file = features_dir / "parquet" / "features.parquet"

    if not parquet_file.exists():
        return {
            "status": "error",
            "message": f"No features found at {parquet_file}",
        }

    df = pd.read_parquet(parquet_file)

    report = {
        "generated_at": pd.Timestamp.now().isoformat(),
        "total_features": len(df),
        "completeness": check_feature_completeness(df),
        "outliers": check_outliers(df),
        "validation": validate_feature_vectors(df, strict=strict),
    }

    # Overall quality score
    completeness_score = report["completeness"]["completeness_score"]
    validation_score = (
        report["validation"]["valid_count"] / report["validation"]["total_validated"] * 100
        if report["validation"]["total_validated"] > 0
        else 0
    )
    report["overall_quality_score"] = (completeness_score + validation_score) / 2

    return report


def print_quality_report(report: dict[str, Any]) -> None:
    """Print a formatted quality report."""
    print("=" * 80)
    print("FEATURE DATA QUALITY REPORT")
    print("=" * 80)
    print(f"Generated at: {report['generated_at']}")
    print(f"Total features: {report['total_features']}")
    print()

    # Completeness
    completeness = report.get("completeness", {})
    print("COMPLETENESS:")
    print(f"  Completeness score: {completeness.get('completeness_score', 0):.1f}%")
    missing = completeness.get("missing_values", {})
    if missing:
        print("  Missing values:")
        for field, info in list(missing.items())[:5]:  # Show first 5
            print(f"    {field}: {info.get('count', 0)} ({info.get('percentage', 0):.1f}%)")
    print()

    # Outliers
    outliers = report.get("outliers", {})
    outlier_data = outliers.get("outliers", {})
    if outlier_data:
        print("OUTLIERS:")
        for field, info in list(outlier_data.items())[:5]:  # Show first 5
            print(f"  {field}: {info.get('count', 0)} outliers ({info.get('percentage', 0):.1f}%)")
    print()

    # Validation
    validation = report.get("validation", {})
    print("VALIDATION:")
    print(f"  Total validated: {validation.get('total_validated', 0)}")
    print(f"  Valid: {validation.get('valid_count', 0)}")
    print(f"  Invalid: {validation.get('invalid_count', 0)}")
    if validation.get("sample_errors"):
        print("  Sample errors:")
        for error in validation["sample_errors"][:3]:  # Show first 3
            print(f"    {error.get('image_path', 'unknown')}: {error.get('errors', [])[:1]}")
    print()

    # Overall quality
    print(f"Overall quality score: {report.get('overall_quality_score', 0):.1f}%")
    print("=" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Check feature data quality")
    parser.add_argument(
        "--features-dir",
        type=Path,
        help="Directory containing features (default: data/features)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file for quality report (default: print to stdout)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Use strict validation mode (treat warnings as errors)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )

    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Set up directory
    if args.features_dir:
        features_dir = args.features_dir
    else:
        project_root = Path(__file__).parent.parent.parent
        features_dir = project_root / "data" / "features"

    # Generate report
    report = generate_quality_report(features_dir, strict=args.strict)

    # Output report
    if args.output:
        with args.output.open("w") as f:
            json.dump(report, f, indent=2, default=str)
        LOGGER.info("Saved quality report to: %s", args.output)
    else:
        if report.get("status") == "error":
            print(f"ERROR: {report.get('message')}")
            sys.exit(1)
        print_quality_report(report)


if __name__ == "__main__":
    main()

