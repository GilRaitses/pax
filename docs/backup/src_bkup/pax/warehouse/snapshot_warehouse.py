"""Build structured snapshot datasets from raw metadata dumps."""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from ..config import PaxSettings

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class SnapshotWarehouse:
    """Aggregate raw snapshot metadata into columnar datasets."""

    settings: PaxSettings

    @classmethod
    def create(cls, settings: PaxSettings | None = None) -> "SnapshotWarehouse":
        cfg = settings or PaxSettings()
        cfg.ensure_dirs()
        return cls(settings=cfg)

    def build(self, *, overwrite: bool = True) -> list[Path]:
        """Build Parquet datasets grouped by capture date.

        Parameters
        ----------
        overwrite:
            If ``True``, replace any existing parquet file for a given day.

        Returns
        -------
        list[Path]
            Paths to the parquet files written during this run.
        """

        metadata_root = self.settings.storage.metadata
        if metadata_root is None or not metadata_root.exists():
            LOGGER.warning("Metadata directory %s does not exist", metadata_root)
            return []

        records = self._load_records(metadata_root.rglob("*.json"))
        if not records:
            LOGGER.info("No snapshot metadata files found under %s", metadata_root)
            return []

        df = pd.DataFrame(records)
        df["captured_at"] = pd.to_datetime(df["captured_at"], utc=True, errors="coerce")
        df.dropna(subset=["captured_at"], inplace=True)
        df["capture_date"] = df["captured_at"].dt.date

        output_root = self.settings.storage.root / "warehouse" / "snapshots"
        output_root.mkdir(parents=True, exist_ok=True)

        written: list[Path] = []
        for date_value, group in df.groupby("capture_date"):
            out_path = output_root / f"{date_value.isoformat()}.parquet"
            if out_path.exists() and not overwrite:
                existing = pd.read_parquet(out_path)
                combined = pd.concat([existing, group], ignore_index=True)
                combined = combined.drop_duplicates(subset=["metadata_path"], keep="last")
                combined.sort_values("captured_at", inplace=True)
                combined.to_parquet(out_path, index=False)
            else:
                group = group.sort_values("captured_at")
                group.to_parquet(out_path, index=False)
            written.append(out_path)
            LOGGER.info("Wrote %d rows to %s", len(group), out_path)

        return written

    def _load_records(self, files: Iterable[Path]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for file_path in files:
            if file_path.name.startswith("batch_"):
                continue
            try:
                payload = json.loads(file_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                LOGGER.warning("Failed to parse %s: %s", file_path, exc)
                continue

            features = payload.get("features", {})
            feature_columns = {
                f"feature_{key}": value for key, value in features.items()
            }

            record = {
                "camera_id": payload.get("camera_id"),
                "captured_at": payload.get("captured_at"),
                "image_path": payload.get("image_path"),
                "image_bytes": payload.get("image_bytes"),
                "image_remote_uri": payload.get("image_remote_uri"),
                "metadata_path": str(file_path.relative_to(self.settings.storage.root)),
                "metadata_extra": json.dumps(payload.get("metadata", {})),
                "cloud_vision_data": json.dumps(payload.get("cloud_vision_data", {})),
                "features_json": json.dumps(features),
                **feature_columns,
            }

            records.append(record)

        return records

