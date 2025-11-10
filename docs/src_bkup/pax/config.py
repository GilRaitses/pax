"""Configuration helpers for Pax projects."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageConfig(BaseModel):
    """Paths for storing collected and processed data."""

    root: Path = Field(default_factory=lambda: Path.cwd() / "data")
    raw: Path | None = None
    processed: Path | None = None
    logs: Path | None = None
    images: Path | None = None
    metadata: Path | None = None

    def ensure(self) -> None:
        """Ensure directories exist on disk."""

        base = self.root
        self.raw = self.raw or (base / "raw")
        self.processed = self.processed or (base / "processed")
        self.logs = self.logs or (base / "logs")
        self.images = self.images or (self.raw / "images")
        self.metadata = self.metadata or (self.raw / "metadata")

        for path in (base, self.raw, self.processed, self.logs, self.images, self.metadata):
            path.mkdir(parents=True, exist_ok=True)


class CameraAPISettings(BaseModel):
    """Configuration for the NYCTMC camera API."""

    api_key: str = Field(default="", description="API key if required (not needed for NYCTMC).")
    base_url: Annotated[str, Field(pattern=r"^https?://")] = (
        "https://webcams.nyctmc.org/api/cameras"
    )
    timeout_seconds: int = 10
    max_retries: int = 3


class RemoteStorageSettings(BaseModel):
    """Optional remote storage configuration for uploaded artifacts."""

    provider: Literal["none", "gcs"] = "none"
    bucket: str | None = None
    prefix: str = "pax"
    credentials_path: Path | None = None

    def is_enabled(self) -> bool:
        return self.provider != "none" and self.bucket is not None


class PaxSettings(BaseSettings):
    """Top-level settings model for the project."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="PAX_", extra="ignore")

    storage: StorageConfig = StorageConfig()
    camera_api: CameraAPISettings = CameraAPISettings()
    sampling_minutes: int = Field(default=30, ge=5, le=180)
    remote: RemoteStorageSettings = RemoteStorageSettings()

    def ensure_dirs(self) -> None:
        """Ensure storage-related directories exist."""

        self.storage.ensure()


settings = PaxSettings()



