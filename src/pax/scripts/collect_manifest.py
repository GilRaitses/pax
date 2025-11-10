"""CLI for collecting data from cameras defined in cameras.yaml manifest."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import yaml

from ..config import PaxSettings
from ..data_collection import CameraDataCollector


def load_manifest(manifest_path: Path) -> dict:
    """Load camera manifest from YAML or JSON file."""
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    with open(manifest_path) as f:
        if manifest_path.suffix.lower() == ".json":
            import json
            return json.load(f)
        else:
            return yaml.safe_load(f)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("cameras.yaml"),
        help="Path to camera manifest YAML or JSON (default: cameras.yaml)",
    )
    parser.add_argument(
        "--skip-images",
        action="store_true",
        help="Skip downloading JPEG frames; only metadata will be stored.",
    )
    parser.add_argument(
        "--gcs-bucket",
        help="Override remote GCS bucket for uploads (enables uploading).",
    )
    parser.add_argument(
        "--gcs-prefix",
        help="Override remote object prefix when uploading to GCS.",
    )
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Disable remote uploads even if configured in the environment.",
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

    # Load manifest
    try:
        manifest = load_manifest(args.manifest)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("\nCreate cameras.yaml with camera IDs to monitor.", file=sys.stderr)
        print("Run 'python -m pax.scripts.collect --dry-run' to list available cameras.", file=sys.stderr)
        return 1

    cameras = manifest.get("cameras", [])
    if not cameras:
        print("Error: No cameras defined in manifest", file=sys.stderr)
        return 1

    camera_ids = [cam["id"] for cam in cameras]
    print(f"Collecting from {len(camera_ids)} cameras defined in manifest...")

    # Configure settings
    settings = PaxSettings()
    if args.no_upload:
        settings.remote.provider = "none"
    elif args.gcs_bucket:
        settings.remote.provider = "gcs"
        settings.remote.bucket = args.gcs_bucket
        if args.gcs_prefix:
            settings.remote.prefix = args.gcs_prefix
    else:
        # Check environment variables (Cloud Run sets these)
        import os
        remote_provider = os.getenv("PAX_REMOTE_PROVIDER") or os.getenv("PAX_REMOTE__PROVIDER")
        remote_bucket = os.getenv("PAX_REMOTE_BUCKET") or os.getenv("PAX_REMOTE__BUCKET")
        remote_prefix = os.getenv("PAX_REMOTE_PREFIX") or os.getenv("PAX_REMOTE__PREFIX")
        if remote_provider == "gcs" and remote_bucket:
            settings.remote.provider = "gcs"
            settings.remote.bucket = remote_bucket
            if remote_prefix:
                settings.remote.prefix = remote_prefix

    # Collect data
    collector = CameraDataCollector.create(settings)
    batch = collector.collect(
        camera_ids=camera_ids,
        download_images=not args.skip_images,
    )

    print(f"Collected {batch.count} snapshots starting at {batch.started_at.isoformat()}.")
    if batch.storage_records:
        print(f"Saved {batch.count} metadata files under {settings.storage.metadata}")
        if not args.skip_images:
            print(f"Downloaded {batch.count} JPEG frames under {settings.storage.images}.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

