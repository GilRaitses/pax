"""Export daily data and send email notification."""

from __future__ import annotations

import argparse
import json
import logging
import smtplib
import sys
import tarfile
from datetime import datetime, timedelta
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from ..config import PaxSettings

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--email",
        required=True,
        help="Email address to send daily report",
    )
    parser.add_argument(
        "--smtp-host",
        default="smtp.gmail.com",
        help="SMTP server host (default: smtp.gmail.com)",
    )
    parser.add_argument(
        "--smtp-port",
        type=int,
        default=587,
        help="SMTP server port (default: 587)",
    )
    parser.add_argument(
        "--smtp-user",
        help="SMTP username (default: same as --email)",
    )
    parser.add_argument(
        "--smtp-password",
        help="SMTP password or app-specific password",
    )
    parser.add_argument(
        "--date",
        help="Date to export (YYYY-MM-DD, default: yesterday)",
    )
    parser.add_argument(
        "--attach-data",
        action="store_true",
        help="Attach compressed data files to email (may be large)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )
    return parser


def export_daily_data(settings: PaxSettings, target_date: datetime) -> dict:
    """Export data for a specific date."""
    date_str = target_date.date().isoformat()
    
    # Ensure directories are initialized
    settings.ensure_dirs()
    
    # Count metadata files
    metadata_root = settings.storage.metadata
    metadata_count = 0
    camera_ids = set()
    
    if metadata_root and metadata_root.exists():
        for camera_dir in metadata_root.iterdir():
            if not camera_dir.is_dir() or camera_dir.name.startswith("batch_"):
                continue
            
            for meta_file in camera_dir.glob("*.json"):
                try:
                    with open(meta_file) as f:
                        data = json.load(f)
                        capture_time = data.get("captured_at", "")
                        if capture_time.startswith(date_str):
                            metadata_count += 1
                            camera_ids.add(camera_dir.name)
                except Exception:
                    continue
    
    # Count images
    image_root = settings.storage.images
    image_count = 0
    
    if image_root and image_root.exists():
        for camera_dir in image_root.iterdir():
            if not camera_dir.is_dir():
                continue
            for img_file in camera_dir.glob("*.jpg"):
                if img_file.stem.startswith(date_str.replace("-", "")):
                    image_count += 1
    
    # Check warehouse
    warehouse_root = settings.storage.root / "warehouse" / "snapshots"
    parquet_file = warehouse_root / f"{date_str}.parquet"
    parquet_exists = parquet_file.exists() if warehouse_root.exists() else False
    parquet_size = parquet_file.stat().st_size if parquet_exists else 0
    
    return {
        "date": date_str,
        "metadata_count": metadata_count,
        "image_count": image_count,
        "unique_cameras": len(camera_ids),
        "parquet_exists": parquet_exists,
        "parquet_size_mb": parquet_size / (1024 * 1024),
        "parquet_path": str(parquet_file) if parquet_exists else None,
    }


def create_archive(settings: PaxSettings, target_date: datetime) -> Path | None:
    """Create compressed archive of daily data."""
    date_str = target_date.date().isoformat()
    export_dir = settings.storage.root / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    
    archive_path = export_dir / f"pax_data_{date_str}.tar.gz"
    
    # Files to include
    files_to_archive = []
    
    # Add warehouse parquet
    warehouse_root = settings.storage.root / "warehouse" / "snapshots"
    parquet_file = warehouse_root / f"{date_str}.parquet"
    if parquet_file.exists():
        files_to_archive.append((parquet_file, f"warehouse/{parquet_file.name}"))
    
    # Add batch metadata
    metadata_root = settings.storage.metadata
    if metadata_root and metadata_root.exists():
        for batch_file in metadata_root.glob(f"batch_{date_str.replace('-', '')}*.json"):
            files_to_archive.append((batch_file, f"batches/{batch_file.name}"))
    
    if not files_to_archive:
        LOGGER.warning("No files to archive for %s", date_str)
        return None
    
    # Create archive
    with tarfile.open(archive_path, "w:gz") as tar:
        for file_path, archive_name in files_to_archive:
            tar.add(file_path, arcname=archive_name)
    
    LOGGER.info("Created archive: %s (%.2f MB)", archive_path, archive_path.stat().st_size / (1024 * 1024))
    return archive_path


def send_email(
    to_email: str,
    subject: str,
    body: str,
    attachment_path: Path | None = None,
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 587,
    smtp_user: str | None = None,
    smtp_password: str | None = None,
) -> None:
    """Send email with optional attachment."""
    msg = MIMEMultipart()
    msg["From"] = smtp_user or to_email
    msg["To"] = to_email
    msg["Subject"] = subject
    
    # Attach body
    msg.attach(MIMEText(body, "plain"))
    
    # Attach file if provided
    if attachment_path and attachment_path.exists():
        with open(attachment_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=attachment_path.name)
        part["Content-Disposition"] = f'attachment; filename="{attachment_path.name}"'
        msg.attach(part)
    
    # Send email
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user or to_email, smtp_password)
        server.send_message(msg)
    
    LOGGER.info("Email sent to %s", to_email)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    
    logging.basicConfig(level=args.log_level.upper(), format="%(levelname)s: %(message)s")
    
    # Determine target date (default: yesterday)
    if args.date:
        target_date = datetime.fromisoformat(args.date)
    else:
        target_date = datetime.now() - timedelta(days=1)
    
    date_str = target_date.date().isoformat()
    
    # Load settings
    settings = PaxSettings()
    
    # Export data
    LOGGER.info("Exporting data for %s", date_str)
    export_data = export_daily_data(settings, target_date)
    
    # Create archive if requested
    archive_path = None
    if args.attach_data:
        archive_path = create_archive(settings, target_date)
    
    # Compose email
    subject = f"Pax NYC Daily Data Export - {date_str}"
    body = f"""Pax NYC Data Collection Report

Date: {date_str}

Summary:
- Metadata files: {export_data['metadata_count']}
- Images captured: {export_data['image_count']}
- Unique cameras: {export_data['unique_cameras']}
- Warehouse parquet: {'Yes' if export_data['parquet_exists'] else 'No'}
"""
    
    if export_data['parquet_exists']:
        body += f"- Parquet size: {export_data['parquet_size_mb']:.2f} MB\n"
        body += f"- Parquet path: {export_data['parquet_path']}\n"
    
    if archive_path:
        body += f"\nAttached: {archive_path.name} ({archive_path.stat().st_size / (1024 * 1024):.2f} MB)\n"
    else:
        body += "\nData files available on server:\n"
        body += f"  - {settings.storage.metadata}\n"
        body += f"  - {settings.storage.images}\n"
        body += f"  - {settings.storage.root / 'warehouse' / 'snapshots'}\n"
    
    body += f"""
Dashboard: http://localhost:8000 (when running)

To download manually:
  cd ~/pax
  tar -czf pax_data_{date_str}.tar.gz data/warehouse/snapshots/{date_str}.parquet

--
Pax NYC Data Collection System
Generated: {datetime.now().isoformat()}
"""
    
    # Send email
    if not args.smtp_password:
        LOGGER.error("SMTP password required. Use --smtp-password or set PAX_SMTP_PASSWORD")
        print(f"\nEmail preview:\n\nTo: {args.email}\nSubject: {subject}\n\n{body}")
        return 1
    
    try:
        send_email(
            to_email=args.email,
            subject=subject,
            body=body,
            attachment_path=archive_path,
            smtp_host=args.smtp_host,
            smtp_port=args.smtp_port,
            smtp_user=args.smtp_user or args.email,
            smtp_password=args.smtp_password,
        )
        print(f"Daily report sent to {args.email}")
        return 0
    except Exception as e:
        LOGGER.exception("Failed to send email")
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

