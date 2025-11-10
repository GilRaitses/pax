#!/usr/bin/env python3
"""Cloud Function to send daily email reminder to download images.

This runs daily via Cloud Scheduler and sends an email with:
- Summary of images collected yesterday
- Download link to package script
- Instructions
"""

import json
import logging
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import requests
from google.cloud import storage

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


def get_yesterday_summary(bucket_name: str, prefix: str = "images") -> dict:
    """Get summary of images collected yesterday."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    
    # Use Eastern time (New York)
    yesterday = datetime.now(ZoneInfo("America/New_York")) - timedelta(days=1)
    date_str = yesterday.strftime("%Y-%m-%d")
    date_start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    date_end = date_start + timedelta(days=1)
    
    blobs = list(bucket.list_blobs(prefix=prefix))
    daily_images = {}
    total = 0
    
    for blob in blobs:
        if not blob.name.endswith((".jpg", ".jpeg")):
            continue
        
        # Parse timestamp from path
        try:
            parts = blob.name.split("/")
            if len(parts) >= 3:
                filename = parts[-1]
                timestamp_str = filename.replace(".jpg", "").replace(".jpeg", "")
                timestamp = datetime.strptime(timestamp_str, "%Y%m%dT%H%M%S")
                
                if date_start <= timestamp < date_end:
                    camera_id = parts[-2]
                    daily_images[camera_id] = daily_images.get(camera_id, 0) + 1
                    total += 1
        except Exception:
            continue
    
    return {
        "date": date_str,
        "total_images": total,
        "cameras": len(daily_images),
        "images_per_camera_avg": round(total / len(daily_images), 1) if daily_images else 0,
    }


def send_email_via_sendgrid(to_email: str, subject: str, body: str, sendgrid_api_key: str) -> None:
    """Send email via SendGrid API."""
    url = "https://api.sendgrid.com/v3/mail/send"
    headers = {
        "Authorization": f"Bearer {sendgrid_api_key}",
        "Content-Type": "application/json",
    }
    
    data = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": os.getenv("FROM_EMAIL", "noreply@pax-nyc.iam.gserviceaccount.com")},
        "subject": subject,
        "content": [{"type": "text/html", "value": body}],
    }
    
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    LOGGER.info("Email sent to %s", to_email)


def send_email_via_smtp(to_email: str, subject: str, body: str, smtp_config: dict) -> None:
    """Send email via SMTP."""
    import smtplib
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_config.get("from", "noreply@pax-nyc.com")
    msg["To"] = to_email
    
    msg.attach(MIMEText(body, "html"))
    
    with smtplib.SMTP(smtp_config["host"], smtp_config.get("port", 587)) as server:
        if smtp_config.get("tls", True):
            server.starttls()
        if smtp_config.get("user"):
            server.login(smtp_config["user"], smtp_config["password"])
        server.send_message(msg)
    
    LOGGER.info("Email sent to %s via SMTP", to_email)


def create_email_body(summary: dict, bucket_name: str) -> str:
    """Create HTML email body."""
    date = summary["date"]
    total = summary["total_images"]
    cameras = summary["cameras"]
    avg = summary["images_per_camera_avg"]
    
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2>📸 Daily Image Collection Summary - {date}</h2>
        
        <div style="background-color: #f4f4f4; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3>Collection Statistics</h3>
            <ul>
                <li><strong>Date:</strong> {date}</li>
                <li><strong>Total Images:</strong> {total:,}</li>
                <li><strong>Cameras:</strong> {cameras}</li>
                <li><strong>Avg Images per Camera:</strong> {avg}</li>
            </ul>
        </div>
        
        <div style="background-color: #e8f4f8; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3>📦 Download Today's Images</h3>
            <p>To package and download all images from {date}, run:</p>
            <pre style="background-color: #fff; padding: 10px; border-radius: 3px; overflow-x: auto;">
python3 -m src.pax.scripts.package_daily_images \\
    --bucket {bucket_name} \\
    --date {date} \\
    --format zip
            </pre>
            <p>Or download directly from GCS:</p>
            <pre style="background-color: #fff; padding: 10px; border-radius: 3px;">
gsutil -m cp -r gs://{bucket_name}/images/*/{date.replace('-', '')}* ./downloads/{date}/
            </pre>
        </div>
        
        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 0.9em;">
            <p>This is an automated reminder from the Pax Image Collection System.</p>
            <p>Bucket: <code>gs://{bucket_name}</code></p>
        </div>
    </body>
    </html>
    """
    return body


def main(request):
    """Cloud Function entry point."""
    try:
        # Get configuration from environment
        bucket_name = os.getenv("PAX_REMOTE_BUCKET", "pax-nyc-images")
        to_email = os.getenv("REMINDER_EMAIL")
        sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
        
        if not to_email:
            LOGGER.error("REMINDER_EMAIL environment variable not set")
            return {"status": "error", "message": "REMINDER_EMAIL not configured"}, 400
        
        # Get yesterday's summary
        summary = get_yesterday_summary(bucket_name)
        
        if summary["total_images"] == 0:
            LOGGER.warning("No images found for yesterday, skipping email")
            return {"status": "skipped", "message": "No images to report"}
        
        # Create email
        subject = f"📸 Daily Image Collection Reminder - {summary['date']}"
        body = create_email_body(summary, bucket_name)
        
        # Send email
        if sendgrid_api_key:
            send_email_via_sendgrid(to_email, subject, body, sendgrid_api_key)
        else:
            # Fallback: use SMTP if configured
            smtp_config = {
                "host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
                "port": int(os.getenv("SMTP_PORT", "587")),
                "user": os.getenv("SMTP_USER"),
                "password": os.getenv("SMTP_PASSWORD"),
                "from": os.getenv("FROM_EMAIL", "noreply@pax-nyc.com"),
                "tls": True,
            }
            if smtp_config["user"]:
                send_email_via_smtp(to_email, subject, body, smtp_config)
            else:
                LOGGER.error("No email method configured (SENDGRID_API_KEY or SMTP_USER)")
                return {"status": "error", "message": "Email not configured"}, 500
        
        return {
            "status": "success",
            "date": summary["date"],
            "total_images": summary["total_images"],
            "email_sent_to": to_email,
        }
        
    except Exception as e:
        LOGGER.exception("Failed to send reminder: %s", e)
        return {"status": "error", "message": str(e)}, 500


if __name__ == "__main__":
    # For local testing
    class MockRequest:
        pass
    
    result = main(MockRequest())
    print(json.dumps(result, indent=2))

