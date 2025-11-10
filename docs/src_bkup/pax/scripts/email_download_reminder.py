"""Send email reminders with download links for GCS files every 6 hours."""

from __future__ import annotations

import argparse
import json
import logging
import smtplib
import sys
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from google.cloud import storage

from ..config import PaxSettings

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--email",
        required=True,
        help="Email address to send reminders",
    )
    parser.add_argument(
        "--smtp-host",
        default="smtp.gmail.com",
        help="SMTP server host",
    )
    parser.add_argument(
        "--smtp-port",
        type=int,
        default=587,
        help="SMTP server port",
    )
    parser.add_argument(
        "--smtp-user",
        help="SMTP username",
    )
    parser.add_argument(
        "--smtp-password",
        help="SMTP password or app-specific password",
    )
    parser.add_argument(
        "--bucket",
        help="GCS bucket name (default: from settings)",
    )
    parser.add_argument(
        "--prefix",
        help="GCS prefix/folder (default: from settings)",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=6,
        help="Hours back to look for files (default: 6)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level",
    )
    return parser


def list_recent_files(bucket_name: str, prefix: str, hours: int = 6) -> list[dict[str, Any]]:
    """List files uploaded in the last N hours."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    recent_files = []
    
    for blob in bucket.list_blobs(prefix=prefix):
        # Get file creation time (timeCreated is in UTC)
        created = blob.time_created
        
        if created and created >= cutoff_time:
            # Generate download URL (signed URL, valid for 7 days)
            download_url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(days=7),
                method="GET"
            )
            
            recent_files.append({
                "name": blob.name,
                "size_mb": blob.size / (1024 * 1024),
                "created": created.isoformat(),
                "download_url": download_url,
            })
    
    return sorted(recent_files, key=lambda x: x["created"], reverse=True)


def send_download_reminder(
    to_email: str,
    files: list[dict[str, Any]],
    bucket_name: str,
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 587,
    smtp_user: str | None = None,
    smtp_password: str | None = None,
) -> None:
    """Send email with download links."""
    
    if not files:
        body = f"""
No new files found in gs://{bucket_name} in the last 6 hours.

Check the bucket: https://console.cloud.google.com/storage/browser/{bucket_name}
"""
    else:
        total_size = sum(f["size_mb"] for f in files)
        
        body = f"""
Pax NYC Data Collection - Download Reminder

New files available for download from gs://{bucket_name}:

Total: {len(files)} files ({total_size:.2f} MB)

Recent Files (last 6 hours):
"""
        
        for file_info in files[:20]:  # Show first 20 files
            body += f"\n• {file_info['name']}\n"
            body += f"  Size: {file_info['size_mb']:.2f} MB\n"
            body += f"  Uploaded: {file_info['created'][:19]} UTC\n"
            body += f"  Download: {file_info['download_url']}\n"
        
        if len(files) > 20:
            body += f"\n... and {len(files) - 20} more files\n"
        
        body += f"""

Download All:
  gsutil -m cp -r gs://{bucket_name}/* ./downloads/

Or view in Cloud Console:
  https://console.cloud.google.com/storage/browser/{bucket_name}

All download links are valid for 7 days.
Files in bucket will be deleted after 7 days.

---
Pax NYC Data Collection System
Generated: {datetime.now().isoformat()}
"""
    
    subject = f"Pax NYC Download Reminder - {len(files)} new files"
    if not files:
        subject = "Pax NYC Download Reminder - No new files"
    
    msg = MIMEMultipart()
    msg["From"] = smtp_user or to_email
    msg["To"] = to_email
    msg["Subject"] = subject
    
    msg.attach(MIMEText(body, "plain"))
    
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user or to_email, smtp_password)
        server.send_message(msg)
    
    LOGGER.info("Download reminder sent to %s (%d files)", to_email, len(files))


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    
    logging.basicConfig(level=args.log_level.upper(), format="%(levelname)s: %(message)s")
    
    # Load settings
    settings = PaxSettings()
    bucket_name = args.bucket or settings.remote.bucket
    prefix = args.prefix or settings.remote.prefix
    
    if not bucket_name:
        LOGGER.error("No bucket specified. Use --bucket or configure PAX_REMOTE_BUCKET")
        return 1
    
    # List recent files
    LOGGER.info("Listing files from gs://%s/%s (last %d hours)", bucket_name, prefix, args.hours)
    try:
        files = list_recent_files(bucket_name, prefix, args.hours)
        LOGGER.info("Found %d files uploaded in the last %d hours", len(files), args.hours)
    except Exception as e:
        LOGGER.exception("Failed to list files from GCS")
        return 1
    
    # Send email
    if not args.smtp_password:
        LOGGER.error("SMTP password required. Use --smtp-password")
        print(f"\nPrepared reminder for {len(files)} files:\n")
        for f in files[:5]:
            print(f"  {f['name']} - {f['size_mb']:.2f} MB")
        return 1
    
    try:
        send_download_reminder(
            to_email=args.email,
            files=files,
            bucket_name=bucket_name,
            smtp_host=args.smtp_host,
            smtp_port=args.smtp_port,
            smtp_user=args.smtp_user or args.email,
            smtp_password=args.smtp_password,
        )
        print(f"Download reminder sent to {args.email} ({len(files)} files)")
        return 0
    except Exception as e:
        LOGGER.exception("Failed to send email")
        return 1


if __name__ == "__main__":
    sys.exit(main())




