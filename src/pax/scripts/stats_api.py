"""Simple HTTP API to serve collection statistics for the dashboard."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import yaml

from ..config import PaxSettings

LOGGER = logging.getLogger(__name__)


class StatsAPIHandler(BaseHTTPRequestHandler):
    """HTTP handler for serving collection statistics."""

    def do_GET(self) -> None:
        """Handle GET requests."""
        if self.path == "/api/stats":
            self.serve_stats()
        elif self.path == "/api/manifest":
            self.serve_manifest()
        elif self.path == "/" or self.path == "/index.html":
            self.serve_index()
        else:
            self.send_error(404)

    def serve_stats(self) -> None:
        """Serve collection statistics as JSON."""
        try:
            settings = PaxSettings()
            stats = self._compute_stats(settings)
            self._send_json(stats)
        except Exception as e:
            LOGGER.exception("Error computing stats")
            self.send_error(500, str(e))

    def serve_manifest(self) -> None:
        """Serve camera manifest as JSON."""
        try:
            manifest_path = Path.cwd() / "cameras.yaml"
            if not manifest_path.exists():
                self._send_json({"cameras": []})
                return

            with open(manifest_path) as f:
                manifest = yaml.safe_load(f)
            self._send_json(manifest)
        except Exception as e:
            LOGGER.exception("Error loading manifest")
            self.send_error(500, str(e))

    def serve_index(self) -> None:
        """Serve the dashboard HTML."""
        try:
            index_path = Path.cwd() / "docs" / "index.html"
            if not index_path.exists():
                self.send_error(404, "Dashboard not found")
                return

            with open(index_path, "rb") as f:
                content = f.read()

            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            LOGGER.exception("Error serving index")
            self.send_error(500, str(e))

    def _compute_stats(self, settings: PaxSettings) -> dict[str, Any]:
        """Compute statistics from metadata files."""
        metadata_root = settings.storage.metadata
        if not metadata_root or not metadata_root.exists():
            return self._empty_stats()

        # Count images per camera
        camera_counts: dict[str, dict] = {}
        total_images = 0
        latest_capture = None

        for camera_dir in metadata_root.iterdir():
            if not camera_dir.is_dir() or camera_dir.name.startswith("batch_"):
                continue

            camera_id = camera_dir.name
            metadata_files = list(camera_dir.glob("*.json"))
            count = len(metadata_files)
            total_images += count

            # Find latest capture time
            last_capture = None
            for meta_file in metadata_files:
                try:
                    with open(meta_file) as f:
                        data = json.load(f)
                        capture_time = data.get("captured_at")
                        if capture_time:
                            if not last_capture or capture_time > last_capture:
                                last_capture = capture_time
                            if not latest_capture or capture_time > latest_capture:
                                latest_capture = capture_time
                except Exception:
                    continue

            camera_counts[camera_id] = {
                "count": count,
                "lastCapture": last_capture,
            }

        # Load manifest to get camera names
        manifest_path = Path.cwd() / "cameras.yaml"
        active_cameras = 0
        if manifest_path.exists():
            with open(manifest_path) as f:
                manifest = yaml.safe_load(f)
                active_cameras = len(manifest.get("cameras", []))

        return {
            "totalImages": total_images,
            "activeCameras": active_cameras,
            "latestCapture": latest_capture,
            "cameraCounts": camera_counts,
            "storageInfo": f"{total_images} images across {len(camera_counts)} cameras",
        }

    def _empty_stats(self) -> dict[str, Any]:
        """Return empty stats structure."""
        return {
            "totalImages": 0,
            "activeCameras": 0,
            "latestCapture": None,
            "cameraCounts": {},
            "storageInfo": "No data collected yet",
        }

    def _send_json(self, data: dict) -> None:
        """Send JSON response."""
        response = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format: str, *args) -> None:
        """Override to use standard logging."""
        LOGGER.info(format, *args)


def main(port: int = 8000) -> None:
    """Start the stats API server."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    server = HTTPServer(("0.0.0.0", port), StatsAPIHandler)
    LOGGER.info("Stats API server running on http://0.0.0.0:%d", port)
    LOGGER.info("Dashboard available at http://localhost:%d/", port)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        LOGGER.info("Shutting down server")
        server.shutdown()


if __name__ == "__main__":
    main()

