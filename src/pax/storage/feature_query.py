"""Feature query and retrieval API.

This module provides functions to query features by camera, time, zone, and other filters.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd

from pax.storage.feature_storage import FeatureStorage

LOGGER = logging.getLogger(__name__)


class FeatureQuery:
    """Query interface for feature vectors."""

    def __init__(self, storage_dir: Path | str, zones_geojson: Path | str | None = None):
        """
        Initialize feature query interface.

        Args:
            storage_dir: Directory where features are stored.
            zones_geojson: Optional path to Voronoi zones GeoJSON file for zone queries.
        """
        self.storage = FeatureStorage(storage_dir, format="parquet")
        self.storage_dir = Path(storage_dir)
        self.zones_gdf = None

        if zones_geojson:
            try:
                self.zones_gdf = gpd.read_file(zones_geojson)
                LOGGER.info("Loaded %d zones from %s", len(self.zones_gdf), zones_geojson)
            except Exception as e:
                LOGGER.warning("Failed to load zones GeoJSON: %s", e)

    def get_features_by_camera(
        self,
        camera_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> pd.DataFrame:
        """
        Get features for a specific camera.

        Args:
            camera_id: Camera ID to filter by.
            start_time: Optional start time filter.
            end_time: Optional end time filter.
            limit: Optional limit on number of results.

        Returns:
            DataFrame with features for the camera.
        """
        parquet_file = self.storage._get_parquet_file_path()
        if not parquet_file.exists():
            LOGGER.warning("No features found in storage")
            return pd.DataFrame()

        df = pd.read_parquet(parquet_file)

        # Filter by camera ID
        if "camera_id" in df.columns:
            df = df[df["camera_id"] == camera_id]
        else:
            LOGGER.warning("camera_id column not found in features")
            return pd.DataFrame()

        # Filter by time range
        if start_time or end_time:
            if "temporal_timestamp" in df.columns:
                df["temporal_timestamp"] = pd.to_datetime(df["temporal_timestamp"])
                if start_time:
                    df = df[df["temporal_timestamp"] >= start_time]
                if end_time:
                    df = df[df["temporal_timestamp"] <= end_time]
            else:
                LOGGER.warning("temporal_timestamp column not found in features")

        if limit:
            df = df.head(limit)

        return df

    def get_features_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
        camera_ids: list[str] | None = None,
        limit: int | None = None,
    ) -> pd.DataFrame:
        """
        Get features within a time range.

        Args:
            start_time: Start time (inclusive).
            end_time: End time (inclusive).
            camera_ids: Optional list of camera IDs to filter by.
            limit: Optional limit on number of results.

        Returns:
            DataFrame with features in the time range.
        """
        parquet_file = self.storage._get_parquet_file_path()
        if not parquet_file.exists():
            LOGGER.warning("No features found in storage")
            return pd.DataFrame()

        df = pd.read_parquet(parquet_file)

        # Filter by time range
        if "temporal_timestamp" in df.columns:
            df["temporal_timestamp"] = pd.to_datetime(df["temporal_timestamp"])
            df = df[(df["temporal_timestamp"] >= start_time) & (df["temporal_timestamp"] <= end_time)]
        else:
            LOGGER.warning("temporal_timestamp column not found in features")
            return pd.DataFrame()

        # Filter by camera IDs
        if camera_ids and "camera_id" in df.columns:
            df = df[df["camera_id"].isin(camera_ids)]

        if limit:
            df = df.head(limit)

        return df

    def get_features_by_zone(
        self,
        zone_id: str | None = None,
        camera_id: str | None = None,
        limit: int | None = None,
    ) -> pd.DataFrame:
        """
        Get features for a specific zone.

        Args:
            zone_id: Zone ID to filter by (if zones GeoJSON is loaded).
            camera_id: Camera ID (zones are mapped 1:1 with cameras).
            limit: Optional limit on number of results.

        Returns:
            DataFrame with features for the zone.
        """
        # If zone_id provided, find corresponding camera_id
        if zone_id and self.zones_gdf is not None:
            zone_row = self.zones_gdf[self.zones_gdf.index.astype(str) == str(zone_id)]
            if not zone_row.empty and "camera_id" in zone_row.columns:
                camera_id = zone_row.iloc[0]["camera_id"]
            else:
                LOGGER.warning("Zone %s not found", zone_id)
                return pd.DataFrame()

        # Use camera_id to query (since zones map 1:1 to cameras)
        if camera_id:
            return self.get_features_by_camera(camera_id, limit=limit)
        else:
            LOGGER.warning("Either zone_id or camera_id must be provided")
            return pd.DataFrame()

    def get_features_by_camera_list(
        self,
        camera_ids: list[str],
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> pd.DataFrame:
        """
        Get features for multiple cameras.

        Args:
            camera_ids: List of camera IDs to filter by.
            start_time: Optional start time filter.
            end_time: Optional end time filter.
            limit: Optional limit on number of results.

        Returns:
            DataFrame with features for the cameras.
        """
        parquet_file = self.storage._get_parquet_file_path()
        if not parquet_file.exists():
            LOGGER.warning("No features found in storage")
            return pd.DataFrame()

        df = pd.read_parquet(parquet_file)

        # Filter by camera IDs
        if "camera_id" in df.columns:
            df = df[df["camera_id"].isin(camera_ids)]
        else:
            LOGGER.warning("camera_id column not found in features")
            return pd.DataFrame()

        # Filter by time range
        if start_time or end_time:
            if "temporal_timestamp" in df.columns:
                df["temporal_timestamp"] = pd.to_datetime(df["temporal_timestamp"])
                if start_time:
                    df = df[df["temporal_timestamp"] >= start_time]
                if end_time:
                    df = df[df["temporal_timestamp"] <= end_time]

        if limit:
            df = df.head(limit)

        return df

    def aggregate_statistics(
        self,
        camera_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        group_by: str | None = None,
    ) -> dict[str, Any]:
        """
        Aggregate statistics for features.

        Args:
            camera_id: Optional camera ID to filter by.
            start_time: Optional start time filter.
            end_time: Optional end time filter.
            group_by: Optional column to group by (e.g., "camera_id", "temporal_hour").

        Returns:
            Dictionary with aggregated statistics.
        """
        # Get base data
        if camera_id:
            df = self.get_features_by_camera(camera_id, start_time=start_time, end_time=end_time)
        else:
            df = self.get_features_by_time_range(start_time or datetime.min, end_time or datetime.max())

        if df.empty:
            return {"count": 0, "message": "No data found"}

        stats = {"count": len(df)}

        # Spatial statistics
        spatial_cols = [
            "spatial_pedestrian_count",
            "spatial_vehicle_count",
            "spatial_bicycle_count",
            "spatial_crowd_density",
        ]
        for col in spatial_cols:
            if col in df.columns:
                stats[f"{col}_mean"] = float(df[col].mean())
                stats[f"{col}_median"] = float(df[col].median())
                stats[f"{col}_std"] = float(df[col].std())
                stats[f"{col}_min"] = float(df[col].min())
                stats[f"{col}_max"] = float(df[col].max())

        # Visual complexity statistics
        visual_cols = [
            "visual_scene_complexity",
            "visual_visibility_score",
            "visual_occlusion_score",
        ]
        for col in visual_cols:
            if col in df.columns:
                stats[f"{col}_mean"] = float(df[col].mean())
                stats[f"{col}_median"] = float(df[col].median())

        # Group by if specified
        if group_by and group_by in df.columns:
            grouped_stats = {}
            for group_value, group_df in df.groupby(group_by):
                group_stats = {
                    "count": len(group_df),
                    "spatial_pedestrian_count_mean": float(group_df["spatial_pedestrian_count"].mean())
                    if "spatial_pedestrian_count" in group_df.columns
                    else None,
                    "spatial_vehicle_count_mean": float(group_df["spatial_vehicle_count"].mean())
                    if "spatial_vehicle_count" in group_df.columns
                    else None,
                    "spatial_crowd_density_mean": float(group_df["spatial_crowd_density"].mean())
                    if "spatial_crowd_density" in group_df.columns
                    else None,
                }
                grouped_stats[str(group_value)] = group_stats
            stats["grouped_by_" + group_by] = grouped_stats

        return stats

    def get_camera_list(self) -> list[str]:
        """
        Get list of all cameras with features.

        Returns:
            List of camera IDs.
        """
        parquet_file = self.storage._get_parquet_file_path()
        if not parquet_file.exists():
            return []

        df = pd.read_parquet(parquet_file)
        if "camera_id" in df.columns:
            return sorted(df["camera_id"].dropna().unique().tolist())
        return []

    def get_time_range(self) -> dict[str, datetime | None]:
        """
        Get the time range of available features.

        Returns:
            Dictionary with 'start_time' and 'end_time'.
        """
        parquet_file = self.storage._get_parquet_file_path()
        if not parquet_file.exists():
            return {"start_time": None, "end_time": None}

        df = pd.read_parquet(parquet_file)
        if "temporal_timestamp" in df.columns:
            df["temporal_timestamp"] = pd.to_datetime(df["temporal_timestamp"])
            return {
                "start_time": df["temporal_timestamp"].min().to_pydatetime(),
                "end_time": df["temporal_timestamp"].max().to_pydatetime(),
            }
        return {"start_time": None, "end_time": None}


# Convenience functions
def get_features_by_camera(
    storage_dir: Path | str,
    camera_id: str,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """Convenience function to get features by camera."""
    query = FeatureQuery(storage_dir)
    return query.get_features_by_camera(camera_id, start_time=start_time, end_time=end_time, limit=limit)


def get_features_by_time_range(
    storage_dir: Path | str,
    start_time: datetime,
    end_time: datetime,
    camera_ids: list[str] | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """Convenience function to get features by time range."""
    query = FeatureQuery(storage_dir)
    return query.get_features_by_time_range(start_time, end_time, camera_ids=camera_ids, limit=limit)


def get_features_by_zone(
    storage_dir: Path | str,
    zone_id: str | None = None,
    camera_id: str | None = None,
    zones_geojson: Path | str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """Convenience function to get features by zone."""
    query = FeatureQuery(storage_dir, zones_geojson=zones_geojson)
    return query.get_features_by_zone(zone_id=zone_id, camera_id=camera_id, limit=limit)


def aggregate_statistics(
    storage_dir: Path | str,
    camera_id: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    group_by: str | None = None,
) -> dict[str, Any]:
    """Convenience function to aggregate statistics."""
    query = FeatureQuery(storage_dir)
    return query.aggregate_statistics(camera_id=camera_id, start_time=start_time, end_time=end_time, group_by=group_by)

