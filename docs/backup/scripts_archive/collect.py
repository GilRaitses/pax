"""CLI for triggering a data collection sweep."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from ..config import PaxSettings
from ..data_collection import CameraDataCollector


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch metadata without persisting snapshot files.",
    )
    parser.add_argument(
        "--camera",
        dest="camera_ids",
        action="append",
        help="Limit collection to specific camera IDs (repeatable).",
    )
    parser.add_argument(
        "--max-cameras",
        type=int,
        help="Only process the first N cameras (after applying filters).",
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

    settings = PaxSettings()
    if args.no_upload:
        settings.remote.provider = "none"
    elif args.gcs_bucket:
        settings.remote.provider = "gcs"
        settings.remote.bucket = args.gcs_bucket
        if args.gcs_prefix:
            settings.remote.prefix = args.gcs_prefix

    collector = CameraDataCollector.create(settings)

    if args.dry_run:
        metadata = collector.client.list_cameras()
        total = len(metadata)
        subset = args.max_cameras if args.max_cameras else total
        print(f"Discovered {total} cameras (showing up to {subset}).")
        if args.max_cameras:
            sample = metadata[: args.max_cameras]
            for item in sample:
                print(f"  - {item.get('id')} :: {item.get('name', 'Unknown')}")
        return 0

    batch = collector.collect(
        camera_ids=args.camera_ids,
        download_images=not args.skip_images,
        max_cameras=args.max_cameras,
    )

    root = settings.storage.root
    image_root = settings.storage.images
    metadata_root = settings.storage.metadata

    print(f"Collected {batch.count} snapshots starting at {batch.started_at.isoformat()}.")
    if batch.storage_records:
        images_saved = sum(1 for record in batch.storage_records if record.get("image_path"))
        metadata_saved = len(batch.storage_records)
        print(f"Saved {metadata_saved} metadata files under {metadata_root}")
        if not args.skip_images:
            print(f"Downloaded {images_saved} JPEG frames under {image_root}.")
        remote_saved = sum(1 for record in batch.storage_records if record.get("image_remote_uri"))
        if remote_saved:
            print(f"Uploaded {remote_saved} frames to remote storage (GCS).")

        preview = batch.storage_records[: min(5, len(batch.storage_records))]
        print("Sample records:")
        for record in preview:
            image_path = record.get("image_path")
            metadata_path = record.get("metadata_path")
            if image_path:
                image_path = Path(root, image_path)
            if metadata_path:
                metadata_path = Path(root, metadata_path)
            remote_uri = record.get("image_remote_uri")
            print(
                f"  - {record['camera_id']} @ {record['captured_at']}:"
                f" metadata={metadata_path}"
                + (f", image={image_path}" if image_path else "")
                + (f", remote={remote_uri}" if remote_uri else "")
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())



