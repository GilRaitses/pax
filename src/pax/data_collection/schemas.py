"""Schemas describing camera data snapshots."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, HttpUrl


class FeatureVector(BaseModel):
    """Quantitative descriptors extracted from a camera frame."""

    pedestrian_density: float = Field(ge=0, description="Estimated pedestrians per frame.")
    bike_lane_violations: float = Field(ge=0, description="Rate of observed bike lane violations.")
    vehicle_volume: float = Field(ge=0, description="Estimated vehicles per frame.")
    obstruction_score: float = Field(ge=0, description="Magnitude of occlusions and blockages.")
    visibility_score: float = Field(ge=0, le=1, description="Normalized visibility metric.")
    stress_score: float | None = Field(
        default=None, description="Optional target label on the 0–30 stress scale."
    )


class CameraSnapshot(BaseModel):
    """Single observation from a NYC DOT traffic camera."""

    camera_id: str = Field(max_length=64)
    captured_at: datetime
    image_url: Annotated[HttpUrl, Field(description="URL for the raw image or video frame.")]
    features: FeatureVector
    metadata: dict[str, str | float | int | bool] = Field(default_factory=dict)


class CameraSnapshotBatch(BaseModel):
    """Batch of snapshots captured during a single sampling sweep."""

    started_at: datetime
    completed_at: datetime
    count: int
    snapshots: list[CameraSnapshot]
    storage_records: list[dict[str, str | None]] | None = None

    @classmethod
    def from_snapshots(
        cls,
        snapshots: list[CameraSnapshot],
        started_at: datetime,
        storage_records: list[dict[str, str | None]] | None = None,
    ) -> """Construct a batch record.""":
        finished = datetime.utcnow()
        return cls(
            started_at=started_at,
            completed_at=finished,
            count=len(snapshots),
            snapshots=snapshots,
            storage_records=storage_records,
        )

