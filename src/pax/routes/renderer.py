"""Render routes with stress gradients on top of map tiles."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Iterable, Sequence

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.patches import Circle
from PIL import Image
import requests
from dotenv import load_dotenv

from ..config import PaxSettings
from .costs import extract_camera_records, load_latest_snapshot_table, stress_along_route
from .definitions import RouteDefinition, ROUTES
from .maps import RoutePoint, fetch_route

LOGGER = logging.getLogger(__name__)


@dataclass
class RenderResult:
    route: RouteDefinition
    output_path: Path
    point_count: int


class RouteRenderer:
    def __init__(self, settings: PaxSettings | None = None) -> None:
        self.settings = settings or PaxSettings()
        self.settings.ensure_dirs()

        load_dotenv(self.settings.model_config.env_file)
        self.api_key = os.getenv("GOOGLE_API_KEY")

    def render_all(
        self,
        *,
        output_dir: Path | None = None,
        warehouse_root: Path | None = None,
    ) -> list[RenderResult]:
        output_dir = output_dir or (Path.cwd() / "outputs" / "figures")
        output_dir.mkdir(parents=True, exist_ok=True)

        df = load_latest_snapshot_table(warehouse_root)
        cameras = extract_camera_records(df) if df is not None else []

        results: list[RenderResult] = []
        for definition in ROUTES.values():
            points = self._fetch_points(definition)
            stress = stress_along_route(points, cameras)
            path = output_dir / f"{definition.slug}_route.png"
            self._render(definition, points, stress, path)
            results.append(RenderResult(route=definition, output_path=path, point_count=len(points)))

        composite = output_dir / "figure4_routes.png"
        self._render_composite(results, composite)
        return results

    def _fetch_points(self, route: RouteDefinition) -> list[RoutePoint]:
        api_key = self._read_api_key()
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY not set; unable to fetch routes")
        LOGGER.info("Fetching polyline for %s", route.title)
        return fetch_route(route.origin, route.destination, route.waypoints, api_key=api_key)

    def _render(
        self,
        route: RouteDefinition,
        points: Sequence[RoutePoint],
        stress: Sequence[float],
        output_path: Path,
    ) -> None:
        if not points:
            raise ValueError("No points to render")

        lats = np.array([p.latitude for p in points])
        lons = np.array([p.longitude for p in points])
        colors = self._stress_to_colors(stress)

        # compute view bounds with padding
        lat_min, lat_max = lats.min(), lats.max()
        lon_min, lon_max = lons.min(), lons.max()
        lat_pad = (lat_max - lat_min) * 0.1 or 0.002
        lon_pad = (lon_max - lon_min) * 0.1 or 0.002
        view_lat_min, view_lat_max = lat_min - lat_pad, lat_max + lat_pad
        view_lon_min, view_lon_max = lon_min - lon_pad, lon_max + lon_pad

        background, extent = self._fetch_static_map(
            center=((lat_min + lat_max) / 2, (lon_min + lon_max) / 2),
            lat_span=view_lat_max - view_lat_min,
            lon_span=view_lon_max - view_lon_min,
        )

        fig, ax = plt.subplots(figsize=(4.2, 4.2), dpi=300)
        if background is not None and extent is not None:
            ax.imshow(background, extent=extent, aspect="auto", zorder=1)
        else:
            ax.set_facecolor("#f5f6f7")

        segments = [
            [(lons[i], lats[i]), (lons[i + 1], lats[i + 1])] for i in range(len(points) - 1)
        ]
        lc = LineCollection(
            segments,
            colors=colors[:-1],
            linewidths=6,
            zorder=3,
            capstyle="round",
            joinstyle="round",
        )
        ax.add_collection(lc)

        circle_radius = max(lon_pad, lat_pad) * 0.25
        ax.add_patch(Circle((lons[0], lats[0]), circle_radius, color="#1abc9c", zorder=5))
        ax.add_patch(Circle((lons[-1], lats[-1]), circle_radius, color="#e74c3c", zorder=5))

        ax.text(lons[0], lats[0], "GC", color="white", fontsize=8, ha="center", va="center", zorder=6)
        ax.text(lons[-1], lats[-1], "CH", color="white", fontsize=8, ha="center", va="center", zorder=6)

        ax.set_xlim(view_lon_min, view_lon_max)
        ax.set_ylim(view_lat_min, view_lat_max)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(route.title, fontsize=10)
        fig.tight_layout()
        fig.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        LOGGER.info("Saved %s (%d points)", output_path, len(points))

    def _render_composite(self, results: Sequence[RenderResult], output_path: Path) -> None:
        fig, axes = plt.subplots(1, len(results), figsize=(12, 4), dpi=300)
        if len(results) == 1:
            axes = [axes]

        for ax, result in zip(axes, results):
            img = Image.open(result.output_path)
            ax.imshow(img)
            ax.axis("off")
            ax.set_title(result.route.title, fontsize=10)

        fig.tight_layout()
        fig.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        LOGGER.info("Saved composite figure to %s", output_path)

    def _stress_to_colors(self, stress: Sequence[float]) -> np.ndarray:
        arr = np.array(stress, dtype=float)
        arr = np.clip(arr, 0.0, 1.0)
        cmap = plt.get_cmap("RdYlGn_r")
        return cmap(arr)

    def _fetch_static_map(self, center: tuple[float, float], lat_span: float, lon_span: float):
        api_key = self._read_api_key()
        if not api_key:
            return None, None

        zoom = self._estimate_zoom(max(lat_span, lon_span))
        params = {
            "center": f"{center[0]},{center[1]}",
            "zoom": zoom,
            "size": "640x640",
            "scale": 2,
            "maptype": "roadmap",
            "style": "feature:poi|visibility:off",
            "key": api_key,
        }

        try:
            response = requests.get("https://maps.googleapis.com/maps/api/staticmap", params=params, timeout=20)
            response.raise_for_status()
        except requests.RequestException as exc:  # pragma: no cover
            LOGGER.warning("Failed to fetch static map: %s", exc)
            return None, None

        img = Image.open(BytesIO(response.content))
        zoom = params["zoom"]
        meters_per_pixel = 156543.03392 * np.cos(center[0] * np.pi / 180) / (2 ** zoom)
        img_width, img_height = img.size
        lat_range = (img_height / 2) * meters_per_pixel / 111320
        lon_range = (img_width / 2) * meters_per_pixel / (111320 * np.cos(center[0] * np.pi / 180))
        extent = [
            center[1] - lon_range,
            center[1] + lon_range,
            center[0] - lat_range,
            center[0] + lat_range,
        ]
        return img, extent

    @staticmethod
    def _estimate_zoom(span: float) -> int:
        if span > 0.03:
            return 13
        if span > 0.02:
            return 14
        if span > 0.01:
            return 15
        return 16

    def _read_api_key(self) -> str | None:
        return self.api_key or os.getenv("GOOGLE_API_KEY")

