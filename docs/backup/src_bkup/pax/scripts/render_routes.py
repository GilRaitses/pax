"""Generate Figure 4 route previews using Google Maps and snapshot data."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from ..config import PaxSettings
from ..routes import RouteRenderer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory for rendered figures (default: outputs/figures)",
    )
    parser.add_argument(
        "--warehouse-root",
        type=Path,
        help="Override data warehouse root (default: data/warehouse/snapshots)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(level=args.log_level.upper(), format="%(levelname)s: %(message)s")

    settings = PaxSettings()
    renderer = RouteRenderer(settings)
    results = renderer.render_all(output_dir=args.output_dir, warehouse_root=args.warehouse_root)

    for result in results:
        print(f"Rendered {result.route.title} → {result.output_path} ({result.point_count} pts)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

