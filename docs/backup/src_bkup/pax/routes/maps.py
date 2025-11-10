"""Utilities for fetching route polylines from Google Directions API."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

import requests

LOGGER = logging.getLogger(__name__)


LatLon = Tuple[float, float]


@dataclass(frozen=True)
class RoutePoint:
    latitude: float
    longitude: float
    index: int


def fetch_route(origin: LatLon, destination: LatLon, waypoints: Sequence[LatLon], *, api_key: str) -> List[RoutePoint]:
    """Fetch a walking route from Google Directions API and return decoded points."""

    params = {
        "origin": f"{origin[0]},{origin[1]}",
        "destination": f"{destination[0]},{destination[1]}",
        "mode": "walking",
        "key": api_key,
    }
    if waypoints:
        params["waypoints"] = "|".join(f"{lat},{lon}" for lat, lon in waypoints)

    response = requests.get("https://maps.googleapis.com/maps/api/directions/json", params=params, timeout=20)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:  # pragma: no cover - network failure
        LOGGER.error("Directions API request failed: %s", exc)
        raise

    payload = response.json()
    if payload.get("status") != "OK":  # pragma: no cover - API failure
        LOGGER.error("Directions API returned status %s", payload.get("status"))
        raise RuntimeError(f"Directions API status: {payload.get('status')}")

    points: List[RoutePoint] = []
    for leg in payload["routes"][0]["legs"]:
        for step in leg.get("steps", []):
            decoded = decode_polyline(step["polyline"]["points"])
            points.extend(decoded)

    deduped: List[RoutePoint] = []
    seen = set()
    for idx, (lat, lon) in enumerate(points):
        key = (round(lat, 6), round(lon, 6))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(RoutePoint(latitude=lat, longitude=lon, index=len(deduped)))

    LOGGER.debug("Fetched %d points for route", len(deduped))
    return deduped


def decode_polyline(polyline_str: str) -> List[LatLon]:
    index, lat, lng = 0, 0, 0
    coordinates: List[LatLon] = []
    changes = {"latitude": 0, "longitude": 0}

    while index < len(polyline_str):
        for unit in ("latitude", "longitude"):
            shift, result = 0, 0
            while True:
                byte = ord(polyline_str[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            changes[unit] = ~(result >> 1) if result & 1 else (result >> 1)
        lat += changes["latitude"]
        lng += changes["longitude"]
        coordinates.append((lat / 1e5, lng / 1e5))

    return coordinates

