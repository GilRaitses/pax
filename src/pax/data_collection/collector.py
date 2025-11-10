"""High-level orchestration for camera data collection."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Iterable
import re

from ..config import PaxSettings
from ..storage import GCSUploader, NullUploader, RemoteUploader
from .camera_client import CameraAPIClient
from .schemas import CameraSnapshot, CameraSnapshotBatch, FeatureVector

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class CameraDataCollector:
    """Collect and persist snapshots from the NYC DOT camera API."""

    settings: PaxSettings
    client: CameraAPIClient
    uploader: RemoteUploader

    @classmethod
    def create(cls, settings: PaxSettings | None = None) -> "CameraDataCollector":
        config = settings or PaxSettings()
        config.ensure_dirs()
        client = CameraAPIClient(config)
        uploader: RemoteUploader
        if config.remote.provider == "gcs" and config.remote.bucket:
            uploader = GCSUploader(bucket=config.remote.bucket, prefix=config.remote.prefix)
        else:
            uploader = NullUploader()
        return cls(settings=config, client=client, uploader=uploader)

    def collect(
        self,
        camera_ids: Iterable[str] | None = None,
        *,
        download_images: bool = True,
        max_cameras: int | None = None,
    ) -> CameraSnapshotBatch:
        """Entry point for a single sampling sweep."""

        # Use Eastern time (New York)
        started_at = datetime.now(ZoneInfo("America/New_York"))
        if camera_ids is None:
            metadata = self.client.list_cameras()
            camera_ids = [item["id"] for item in metadata]
        else:
            camera_ids = list(camera_ids)

        if max_cameras is not None:
            camera_ids = list(camera_ids)[:max_cameras]

        raw_snapshots = self.client.fetch_snapshots(camera_ids)
        snapshots = [self._parse_snapshot(s) for s in raw_snapshots]
        storage_records: list[dict[str, str | None]] = []

        for snapshot in snapshots:
            storage_records.append(self._store_snapshot(snapshot, download_images=download_images))

        batch = CameraSnapshotBatch.from_snapshots(
            snapshots,
            started_at,
            storage_records=storage_records,
        )
        self._persist_batch(batch, storage_records)
        return batch

    def _parse_snapshot(self, payload: dict) -> CameraSnapshot:
        features = FeatureVector(
            pedestrian_density=payload.get("pedestrian_density", 0.0),
            bike_lane_violations=payload.get("bike_lane_violations", 0.0),
            vehicle_volume=payload.get("vehicle_volume", 0.0),
            obstruction_score=payload.get("obstruction_score", 0.0),
            visibility_score=payload.get("visibility_score", 1.0),
            stress_score=payload.get("stress_score"),
        )

        # Flatten metadata to only include simple types
        simple_metadata = {}
        for key, value in payload.items():
            if key in {
                "camera_id",
                "captured_at",
                "image_url",
                "pedestrian_density",
                "bike_lane_violations",
                "vehicle_volume",
                "obstruction_score",
                "visibility_score",
                "stress_score",
                "metadata",  # Skip nested metadata dict
            }:
                continue
            if isinstance(value, (str, int, float, bool)):
                simple_metadata[key] = value
        
        snapshot = CameraSnapshot(
            camera_id=str(payload.get("camera_id")),
            captured_at=datetime.fromisoformat(payload["captured_at"]),
            image_url=payload["image_url"],
            features=features,
            metadata=simple_metadata,
        )

        return snapshot

    def _store_snapshot(
        self, snapshot: CameraSnapshot, *, download_images: bool = True
    ) -> dict[str, str | None]:
        # Convert to Eastern time for filename
        captured_at_et = snapshot.captured_at.astimezone(ZoneInfo("America/New_York"))
        timestamp_slug = captured_at_et.strftime("%Y%m%dT%H%M%S")
        camera_slug = self._slugify(snapshot.camera_id)

        image_path: Path | None = None
        remote_uri: str | None = None
        image_bytes = None
        if download_images and snapshot.image_url:
            try:
                image_bytes = self.client.download_image(snapshot.image_url)
                image_dir = (self.settings.storage.images or Path()).joinpath(camera_slug)
                image_dir.mkdir(parents=True, exist_ok=True)
                image_path = image_dir / f"{timestamp_slug}.jpg"
                image_path.write_bytes(image_bytes)
                remote_uri = self._maybe_upload(image_path, camera_slug, timestamp_slug)
            except Exception as exc:  # pragma: no cover - network failures
                LOGGER.warning(
                    "Failed to download image", extra={"camera_id": snapshot.camera_id, "error": str(exc)}
                )

        metadata_dir = (self.settings.storage.metadata or Path()).joinpath(camera_slug)
        metadata_dir.mkdir(parents=True, exist_ok=True)
        metadata_path = metadata_dir / f"{timestamp_slug}.json"

        record = snapshot.model_dump(mode="json")
        record["image_path"] = str(image_path) if image_path else None
        record["image_bytes"] = len(image_bytes) if image_bytes else None
        record["image_remote_uri"] = remote_uri

        with metadata_path.open("w", encoding="utf-8") as file:
            json.dump(record, file, indent=2)

        root = self.settings.storage.root
        return {
            "camera_id": snapshot.camera_id,
            "captured_at": snapshot.captured_at.astimezone(ZoneInfo("America/New_York")).isoformat(),
            "image_path": str(image_path.relative_to(root)) if image_path else None,
            "image_remote_uri": remote_uri,
            "metadata_path": str(metadata_path.relative_to(root)),
        }

    def _persist_batch(
        self, batch: CameraSnapshotBatch, storage_records: list[dict[str, str | None]]
    ) -> None:
        # Use Eastern time for batch filename
        started_at_et = batch.started_at.astimezone(ZoneInfo("America/New_York"))
        timestamp = started_at_et.strftime("%Y%m%dT%H%M%S")
        out_dir = self.settings.storage.raw or (self.settings.storage.root / "raw")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"snapshots_{timestamp}.json"
        LOGGER.info("Writing batch to %s", out_path)
        serialized = batch.model_dump(mode="json")
        with Path(out_path).open("w", encoding="utf-8") as file:
            json.dump(serialized, file, indent=2)

        manifest_path = (self.settings.storage.metadata or Path()) / f"batch_{timestamp}.json"
        manifest = {
            "started_at": batch.started_at.astimezone(ZoneInfo("America/New_York")).isoformat(),
            "completed_at": batch.completed_at.astimezone(ZoneInfo("America/New_York")).isoformat(),
            "count": batch.count,
            "storage_records": storage_records,
        }
        with manifest_path.open("w", encoding="utf-8") as file:
            json.dump(manifest, file, indent=2)

    @staticmethod
    def _slugify(value: str) -> str:
        slug = re.sub(r"[^A-Za-z0-9_-]+", "-", value.strip())
        return slug or "unknown"

    def _maybe_upload(self, image_path: Path, camera_slug: str, timestamp_slug: str) -> str | None:
        remote_key = f"{camera_slug}/{timestamp_slug}.jpg"
        try:
            return self.uploader.upload_file(image_path, remote_key)
        except Exception as exc:  # pragma: no cover - remote failures
            LOGGER.warning("Remote upload failed", extra={"path": str(image_path), "error": str(exc)})
            return None


__all__ = ["CameraDataCollector"]



