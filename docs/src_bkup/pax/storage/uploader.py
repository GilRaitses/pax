"""Remote upload helpers."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Protocol

from google.cloud import storage

LOGGER = logging.getLogger(__name__)


class RemoteUploader(ABC):
    """Interface for uploading collected artifacts to remote storage."""

    @abstractmethod
    def upload_file(self, local_path: Path, remote_key: str) -> str | None:
        """Upload the file and return a URI if available."""


class NullUploader(RemoteUploader):
    """No-op uploader used when remote storage is disabled."""

    def upload_file(self, local_path: Path, remote_key: str) -> str | None:  # noqa: ARG002
        return None


class GCSUploader(RemoteUploader):
    """Upload artifacts to Google Cloud Storage."""

    def __init__(self, bucket: str, prefix: str = "pax") -> None:
        self._client = storage.Client()
        self._bucket = self._client.bucket(bucket)
        self._prefix = prefix.rstrip("/")

    def upload_file(self, local_path: Path, remote_key: str) -> str:
        blob_path = f"{self._prefix}/{remote_key}" if self._prefix else remote_key
        blob = self._bucket.blob(blob_path)
        LOGGER.debug("Uploading %s to gs://%s/%s", local_path, self._bucket.name, blob_path)
        blob.upload_from_filename(local_path)
        return f"gs://{self._bucket.name}/{blob_path}"

