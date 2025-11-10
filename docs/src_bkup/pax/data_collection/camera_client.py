"""Client for interacting with the NYCTMC traffic camera API."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import datetime
from typing import Any

import requests
from requests.adapters import HTTPAdapter, Retry

from ..config import PaxSettings

LOGGER = logging.getLogger(__name__)


class CameraAPIClient:
    """Minimal wrapper around the NYCTMC camera data endpoints."""

    def __init__(self, settings: PaxSettings | None = None) -> None:
        self._settings = settings or PaxSettings()
        self._session = requests.Session()
        retries = Retry(
            total=self._settings.camera_api.max_retries,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        adapter = HTTPAdapter(max_retries=retries)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

    def list_cameras(self) -> list[dict[str, Any]]:
        """Return camera metadata from NYCTMC API."""

        LOGGER.debug("Requesting camera metadata", extra={"url": self._settings.camera_api.base_url})
        response = self._session.get(
            self._settings.camera_api.base_url,
            timeout=self._settings.camera_api.timeout_seconds,
        )
        response.raise_for_status()
        cameras = response.json()
        
        # Filter to only online cameras
        online_cameras = [cam for cam in cameras if cam.get("isOnline") == "true"]
        
        LOGGER.info("Fetched %d camera records (%d online)", len(cameras), len(online_cameras))
        return online_cameras

    def fetch_snapshots(self, camera_ids: Iterable[str]) -> list[dict[str, Any]]:
        """Fetch snapshot data for a collection of camera IDs from NYCTMC.
        
        NYCTMC returns all camera data including image URLs in list_cameras(),
        so we filter that response for the requested IDs.
        """
        all_cameras = self.list_cameras()
        camera_map = {cam["id"]: cam for cam in all_cameras}
        
        snapshots: list[dict[str, Any]] = []
        for camera_id in camera_ids:
            if camera_id not in camera_map:
                LOGGER.warning("Camera %s not found in NYCTMC response", camera_id)
                continue
            
            cam_data = camera_map[camera_id]
            snapshot = {
                "camera_id": camera_id,
                "captured_at": datetime.utcnow().isoformat(),
                "image_url": cam_data.get("imageUrl", ""),
                "name": cam_data.get("name", ""),
                "latitude": cam_data.get("latitude", 0.0),
                "longitude": cam_data.get("longitude", 0.0),
                "area": cam_data.get("area", ""),
                "metadata": cam_data,
            }
            snapshots.append(snapshot)
        
        LOGGER.info("Fetched %d snapshots", len(snapshots))
        return snapshots

    def download_image(self, url: str) -> bytes:
        """Download the raw image bytes from a camera snapshot URL."""

        LOGGER.debug("Downloading image", extra={"url": url})
        response = self._session.get(url, timeout=self._settings.camera_api.timeout_seconds)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("image/"):
            msg = f"Expected image content-type, received {content_type or 'unknown'}"
            raise ValueError(msg)

        return response.content


__all__ = ["CameraAPIClient"]



