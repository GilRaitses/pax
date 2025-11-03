"""Estimate stress values along a route using collected snapshot data."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import numpy as np
import pandas as pd

from .maps import RoutePoint

LOGGER = logging.getLogger(__name__)


@dataclass
class CameraRecord:
    camera_id: str
    latitude: float
    longitude: float
    stress: float


def load_latest_snapshot_table(data_root: Path | None = None) -> pd.DataFrame | None:
    data_root = data_root or Path.cwd() / "data" / "warehouse" / "snapshots"
    if not data_root.exists():
        LOGGER.warning("Warehouse directory %s does not exist", data_root)
        return None

    parquet_files = sorted(data_root.glob("*.parquet"))
    if not parquet_files:
        LOGGER.warning("No parquet files found under %s", data_root)
        return None

    latest = parquet_files[-1]
    LOGGER.info("Loading snapshot parquet %s", latest)
    return pd.read_parquet(latest)


def extract_camera_records(df: pd.DataFrame) -> List[CameraRecord]:
    if df is None or df.empty:
        return []

    df = df.sort_values("captured_at").drop_duplicates(subset=["camera_id"], keep="last")
    records: List[CameraRecord] = []

    for _, row in df.iterrows():
        stress = row.get("feature_stress_score")
        if pd.isna(stress):
            stress = row.get("feature_temperature", np.nan)

        metadata_raw = row.get("metadata_extra")
        lat = row.get("feature_latitude") if "feature_latitude" in row else np.nan
        lon = row.get("feature_longitude") if "feature_longitude" in row else np.nan

        if metadata_raw:
            try:
                metadata = json.loads(metadata_raw)
                lat = metadata.get("latitude") if lat is np.nan else lat
                lon = metadata.get("longitude") if lon is np.nan else lon
            except json.JSONDecodeError:
                pass

        if pd.isna(stress) or pd.isna(lat) or pd.isna(lon):
            continue

        records.append(
            CameraRecord(
                camera_id=row.get("camera_id", "unknown"),
                latitude=float(lat),
                longitude=float(lon),
                stress=float(stress),
            )
        )

    LOGGER.info("Loaded %d camera records with stress scores", len(records))
    return records


def stress_along_route(points: List[RoutePoint], cameras: List[CameraRecord]) -> List[float]:
    if not points:
        return []

    if not cameras:
        LOGGER.warning("No camera records available; using normalized progress as stress")
        return [point.index / max(1, len(points) - 1) for point in points]

    camera_coords = np.array([[cam.latitude, cam.longitude] for cam in cameras])
    camera_stress = np.array([cam.stress for cam in cameras])

    values: List[float] = []
    for point in points:
        deltas = camera_coords - np.array([point.latitude, point.longitude])
        dists = np.linalg.norm(deltas, axis=1)
        idx = int(np.argmin(dists))
        values.append(camera_stress[idx])

    arr = np.array(values, dtype=float)
    if arr.ptp() > 0:
        arr = (arr - arr.min()) / arr.ptp()
    else:
        arr = np.zeros_like(arr)

    return arr.tolist()

