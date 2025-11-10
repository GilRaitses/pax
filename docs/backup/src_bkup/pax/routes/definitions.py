"""Canonical route definitions for the Manhattan corridor case study."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple


LatLon = Tuple[float, float]


@dataclass(frozen=True)
class RouteDefinition:
    slug: str
    title: str
    origin: LatLon
    destination: LatLon
    waypoints: List[LatLon] = field(default_factory=list)
    description: str = ""


ROUTES: dict[str, RouteDefinition] = {
    "baseline": RouteDefinition(
        slug="baseline",
        title="Baseline",
        origin=(40.7527, -73.9772),  # Grand Central
        destination=(40.7651, -73.9799),  # Carnegie Hall
        waypoints=[
            (40.7536, -73.9832),  # 42nd & 6th (Bryant Park)
            (40.7550, -73.9865),  # 42nd & 7th
        ],
        description="Baseline Manhattan distance route via Bryant Park and 7th Ave.",
    ),
    "learned": RouteDefinition(
        slug="learned",
        title="Learned",
        origin=(40.7527, -73.9772),
        destination=(40.7651, -73.9799),
        waypoints=[
            (40.7545, -73.9772),  # 45th & Park
            (40.7545, -73.9785),  # 45th & Madison
            (40.7633, -73.9785),  # 55th & Madison
            (40.7633, -73.9810),  # 55th & 6th
            (40.7651, -73.9810),  # 57th & 6th
        ],
        description="Perception-aware route that avoids stress along 42nd Street.",
    ),
    "alternative": RouteDefinition(
        slug="alternative",
        title="Alternative",
        origin=(40.7527, -73.9772),
        destination=(40.7651, -73.9799),
        waypoints=[
            (40.7590, -73.9772),  # 50th & Park
            (40.7678, -73.9772),  # 59th & Park
            (40.7678, -73.9799),  # 59th & 7th
        ],
        description="Diagonal mix strategy climbing Park Ave before cutting west.",
    ),
}

