"""CLI for building structured warehouse datasets from raw snapshots."""

from __future__ import annotations

import argparse
import logging
import sys

from ..config import PaxSettings
from ..warehouse import SnapshotWarehouse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-overwrite",
        dest="overwrite",
        action="store_false",
        help="Append to existing daily parquet files instead of overwriting.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (DEBUG, INFO, WARNING, ERROR).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(level=args.log_level.upper(), format="%(levelname)s: %(message)s")

    settings = PaxSettings()
    warehouse = SnapshotWarehouse.create(settings)
    written = warehouse.build(overwrite=args.overwrite)

    if written:
        print("Generated parquet files:")
        for path in written:
            print(f"  - {path}")
    else:
        print("No parquet files generated (no metadata found).")

    return 0


if __name__ == "__main__":
    sys.exit(main())

