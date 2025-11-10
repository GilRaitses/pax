"""Feature storage module supporting JSON and Parquet formats.

This module provides functionality to store and retrieve feature vectors
using the FeatureVector schema from BRANCH 2.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import ValidationError

from pax.schemas.feature_vector import FeatureVector

LOGGER = logging.getLogger(__name__)


class FeatureStorage:
    """Storage manager for feature vectors supporting JSON and Parquet formats."""

    def __init__(self, storage_dir: Path | str, format: str = "parquet"):
        """
        Initialize feature storage.

        Args:
            storage_dir: Directory where features will be stored.
            format: Storage format ("json", "parquet", or "both").
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.format = format

        if format not in {"json", "parquet", "both"}:
            raise ValueError(f"Invalid format: {format}. Must be 'json', 'parquet', or 'both'")

    def save_feature_vector(
        self,
        feature_vector: FeatureVector | dict[str, Any],
        image_path: str | Path,
        camera_id: str | None = None,
        zone_id: str | None = None,
        append: bool = True,
    ) -> dict[str, Path]:
        """
        Save a single feature vector.

        Args:
            feature_vector: FeatureVector instance or dictionary.
            image_path: Path to the source image.
            camera_id: Optional camera ID.
            zone_id: Optional zone ID.
            append: If True, append to existing file; if False, overwrite.

        Returns:
            Dictionary mapping format names to saved file paths.
        """
        # Convert to FeatureVector if needed
        if isinstance(feature_vector, dict):
            try:
                feature_vector = FeatureVector.model_validate(feature_vector)
            except ValidationError as e:
                LOGGER.error("Invalid feature vector: %s", e)
                raise

        # Prepare metadata
        metadata = {
            "image_path": str(image_path),
            "camera_id": camera_id,
            "zone_id": zone_id,
            "extracted_at": datetime.now().isoformat(),
        }

        saved_files = {}

        # Save JSON format
        if self.format in {"json", "both"}:
            json_file = self._get_json_file_path(image_path, camera_id)
            self._save_json(feature_vector, metadata, json_file, append=append)
            saved_files["json"] = json_file

        # Save Parquet format
        if self.format in {"parquet", "both"}:
            parquet_file = self._get_parquet_file_path()
            self._save_parquet(feature_vector, metadata, parquet_file, append=append)
            saved_files["parquet"] = parquet_file

        return saved_files

    def save_feature_vectors_batch(
        self,
        feature_vectors: list[FeatureVector | dict[str, Any]],
        image_paths: list[str | Path],
        camera_ids: list[str | None] | None = None,
        zone_ids: list[str | None] | None = None,
        append: bool = True,
    ) -> dict[str, Path]:
        """
        Save multiple feature vectors in batch.

        Args:
            feature_vectors: List of FeatureVector instances or dictionaries.
            image_paths: List of image paths.
            camera_ids: Optional list of camera IDs.
            zone_ids: Optional list of zone IDs.
            append: If True, append to existing file; if False, overwrite.

        Returns:
            Dictionary mapping format names to saved file paths.
        """
        if len(feature_vectors) != len(image_paths):
            raise ValueError("feature_vectors and image_paths must have the same length")

        if camera_ids and len(camera_ids) != len(feature_vectors):
            raise ValueError("camera_ids must have the same length as feature_vectors")

        if zone_ids and len(zone_ids) != len(feature_vectors):
            raise ValueError("zone_ids must have the same length as feature_vectors")

        # Convert to FeatureVector instances
        validated_vectors = []
        for fv in feature_vectors:
            if isinstance(fv, dict):
                try:
                    validated_vectors.append(FeatureVector.model_validate(fv))
                except ValidationError as e:
                    LOGGER.error("Invalid feature vector: %s", e)
                    raise
            else:
                validated_vectors.append(fv)

        saved_files = {}

        # Save JSON format (one file per feature vector)
        if self.format in {"json", "both"}:
            for i, (fv, img_path) in enumerate(zip(validated_vectors, image_paths)):
                camera_id = camera_ids[i] if camera_ids else None
                zone_id = zone_ids[i] if zone_ids else None
                metadata = {
                    "image_path": str(img_path),
                    "camera_id": camera_id,
                    "zone_id": zone_id,
                    "extracted_at": datetime.now().isoformat(),
                }
                json_file = self._get_json_file_path(img_path, camera_id)
                self._save_json(fv, metadata, json_file, append=False)  # Individual files

        # Save Parquet format (single file with all vectors)
        if self.format in {"parquet", "both"}:
            parquet_file = self._get_parquet_file_path()
            self._save_parquet_batch(validated_vectors, image_paths, camera_ids, zone_ids, parquet_file, append=append)
            saved_files["parquet"] = parquet_file

        return saved_files

    def _get_json_file_path(self, image_path: str | Path, camera_id: str | None = None) -> Path:
        """Get JSON file path for a feature vector."""
        image_path = Path(image_path)
        if camera_id:
            json_dir = self.storage_dir / "json" / camera_id
        else:
            json_dir = self.storage_dir / "json"
        json_dir.mkdir(parents=True, exist_ok=True)

        # Use image filename with .json extension
        json_file = json_dir / f"{image_path.stem}.json"
        return json_file

    def _get_parquet_file_path(self) -> Path:
        """Get Parquet file path."""
        parquet_dir = self.storage_dir / "parquet"
        parquet_dir.mkdir(parents=True, exist_ok=True)
        return parquet_dir / "features.parquet"

    def _save_json(
        self,
        feature_vector: FeatureVector,
        metadata: dict[str, Any],
        json_file: Path,
        append: bool = True,
    ) -> None:
        """Save feature vector as JSON."""
        data = {
            "metadata": metadata,
            "feature_vector": feature_vector.model_dump(),
        }

        with json_file.open("w") as f:
            json.dump(data, f, indent=2, default=str)

    def _save_parquet(
        self,
        feature_vector: FeatureVector,
        metadata: dict[str, Any],
        parquet_file: Path,
        append: bool = True,
    ) -> None:
        """Save feature vector to Parquet file."""
        # Flatten feature vector for Parquet
        row = self._flatten_feature_vector(feature_vector, metadata)

        df = pd.DataFrame([row])

        if append and parquet_file.exists():
            existing_df = pd.read_parquet(parquet_file)
            df = pd.concat([existing_df, df], ignore_index=True)

        df.to_parquet(parquet_file, index=False)

    def _save_parquet_batch(
        self,
        feature_vectors: list[FeatureVector],
        image_paths: list[str | Path],
        camera_ids: list[str | None] | None,
        zone_ids: list[str | None] | None,
        parquet_file: Path,
        append: bool = True,
    ) -> None:
        """Save multiple feature vectors to Parquet file."""
        rows = []
        for i, fv in enumerate(feature_vectors):
            metadata = {
                "image_path": str(image_paths[i]),
                "camera_id": camera_ids[i] if camera_ids else None,
                "zone_id": zone_ids[i] if zone_ids else None,
                "extracted_at": datetime.now().isoformat(),
            }
            row = self._flatten_feature_vector(fv, metadata)
            rows.append(row)

        df = pd.DataFrame(rows)

        if append and parquet_file.exists():
            existing_df = pd.read_parquet(parquet_file)
            df = pd.concat([existing_df, df], ignore_index=True)

        df.to_parquet(parquet_file, index=False)

    def _flatten_feature_vector(self, feature_vector: FeatureVector, metadata: dict[str, Any]) -> dict[str, Any]:
        """Flatten FeatureVector to a dictionary suitable for Parquet storage."""
        row = {
            # Metadata
            "image_path": metadata.get("image_path"),
            "camera_id": metadata.get("camera_id"),
            "zone_id": metadata.get("zone_id"),
            "extracted_at": metadata.get("extracted_at"),
            # Spatial features
            "spatial_pedestrian_count": feature_vector.spatial.pedestrian_count,
            "spatial_vehicle_count": feature_vector.spatial.vehicle_count,
            "spatial_bicycle_count": feature_vector.spatial.bicycle_count,
            "spatial_total_object_count": feature_vector.spatial.total_object_count,
            "spatial_pedestrian_density": feature_vector.spatial.pedestrian_density,
            "spatial_vehicle_density": feature_vector.spatial.vehicle_density,
            "spatial_crowd_density": feature_vector.spatial.crowd_density,
            "spatial_object_density": feature_vector.spatial.object_density,
            # Visual complexity features
            "visual_scene_complexity": feature_vector.visual_complexity.scene_complexity,
            "visual_noise": feature_vector.visual_complexity.visual_noise,
            "visual_lighting_condition": feature_vector.visual_complexity.lighting_condition,
            "visual_lighting_brightness": feature_vector.visual_complexity.lighting_brightness,
            "visual_weather_condition": feature_vector.visual_complexity.weather_condition,
            "visual_visibility_score": feature_vector.visual_complexity.visibility_score,
            "visual_occlusion_score": feature_vector.visual_complexity.occlusion_score,
            # Temporal features
            "temporal_timestamp": feature_vector.temporal.timestamp.isoformat(),
            "temporal_hour": feature_vector.temporal.hour,
            "temporal_minute": feature_vector.temporal.minute,
            "temporal_day_of_week": feature_vector.temporal.day_of_week,
            "temporal_is_weekend": feature_vector.temporal.is_weekend,
            "temporal_is_rush_hour": feature_vector.temporal.is_rush_hour,
            "temporal_time_of_day_encoding": feature_vector.temporal.time_of_day_encoding,
            "temporal_day_of_week_encoding": feature_vector.temporal.day_of_week_encoding,
        }

        # Optional CLIP features
        if feature_vector.clip_embedding is not None:
            row["clip_embedding"] = json.dumps(feature_vector.clip_embedding)
            row["clip_embedding_dim"] = len(feature_vector.clip_embedding)
        else:
            row["clip_embedding"] = None
            row["clip_embedding_dim"] = None

        if feature_vector.semantic_scores is not None:
            row["semantic_scores"] = json.dumps(feature_vector.semantic_scores)
        else:
            row["semantic_scores"] = None

        if feature_vector.model_metadata is not None:
            row["model_metadata"] = json.dumps(feature_vector.model_metadata)
        else:
            row["model_metadata"] = None

        return row

    def load_feature_vectors(
        self,
        format: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Load feature vectors from storage.

        Args:
            format: Format to load from ("json", "parquet", or None for auto-detect).
            limit: Maximum number of vectors to load.

        Returns:
            List of feature vector dictionaries.
        """
        format_to_use = format or self.format

        if format_to_use == "parquet":
            return self._load_parquet(limit=limit)
        elif format_to_use == "json":
            return self._load_json(limit=limit)
        else:
            # Try Parquet first, fallback to JSON
            try:
                return self._load_parquet(limit=limit)
            except FileNotFoundError:
                return self._load_json(limit=limit)

    def _load_parquet(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Load feature vectors from Parquet file."""
        parquet_file = self._get_parquet_file_path()
        if not parquet_file.exists():
            raise FileNotFoundError(f"Parquet file not found: {parquet_file}")

        df = pd.read_parquet(parquet_file)
        if limit:
            df = df.head(limit)

        # Convert back to feature vector dictionaries
        feature_vectors = []
        for _, row in df.iterrows():
            fv_dict = self._unflatten_feature_vector(row.to_dict())
            feature_vectors.append(fv_dict)

        return feature_vectors

    def _load_json(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Load feature vectors from JSON files."""
        json_dir = self.storage_dir / "json"
        if not json_dir.exists():
            raise FileNotFoundError(f"JSON directory not found: {json_dir}")

        feature_vectors = []
        json_files = list(json_dir.rglob("*.json"))
        if limit:
            json_files = json_files[:limit]

        for json_file in json_files:
            try:
                with json_file.open("r") as f:
                    data = json.load(f)
                    feature_vectors.append(data.get("feature_vector", data))
            except Exception as e:
                LOGGER.warning("Failed to load JSON file %s: %s", json_file, e)

        return feature_vectors

    def _unflatten_feature_vector(self, row: dict[str, Any]) -> dict[str, Any]:
        """Convert flattened Parquet row back to FeatureVector dictionary format."""
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
                "timestamp": row.get("temporal_timestamp"),
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
        if row.get("clip_embedding"):
            fv_dict["clip_embedding"] = json.loads(row["clip_embedding"])

        if row.get("semantic_scores"):
            fv_dict["semantic_scores"] = json.loads(row["semantic_scores"])

        if row.get("model_metadata"):
            fv_dict["model_metadata"] = json.loads(row["model_metadata"])

        return fv_dict

