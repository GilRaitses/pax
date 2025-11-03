# Midnight Email Notification Setup

## Overview

Automatically receive a daily email at midnight with:
- Summary of data collected that day
- Metadata count, image count, unique cameras
- Warehouse parquet file status
- Optional: Compressed data attachment

## Quick Setup

```bash
cd ~/pax
./setup_midnight_email.sh
```

Follow the prompts to configure:
1. Your email address
2. Email provider (Gmail, Outlook, or custom)
3. SMTP password/app password
4. Whether to attach data files

## Manual Setup

### 1. Get App Password

**For Gmail:**
1. Go to https://myaccount.google.com/apppasswords
2. Select "Mail" and "Mac" (or "Other")
3. Generate password
4. Copy the 16-character password

**For Outlook/Office365:**
- Use your regular account password
- May need to enable "SMTP AUTH" in settings

### 2. Test Email Manually

```bash
cd ~/pax
source venv/bin/activate

python -m pax.scripts.daily_export \
    --email your.email@gmail.com \
    --smtp-password "your-app-password"
```

This sends yesterday's report (default behavior).

### 3. Setup Cron Job

```bash
# Edit crontab
crontab -e

# Add this line (replace paths):
0 0 * * * cd ~/pax && source venv/bin/activate && python -m pax.scripts.daily_export --email your.email@gmail.com --smtp-password "your-app-password" >> ~/.pax_email.log 2>&1
```

## Command Options

```bash
python -m pax.scripts.daily_export \
    --email your.email@gmail.com \              # Required: recipient email
    --smtp-host smtp.gmail.com \                # SMTP server (default: gmail)
    --smtp-port 587 \                           # SMTP port (default: 587)
    --smtp-user your.email@gmail.com \          # SMTP username (default: same as --email)
    --smtp-password "your-app-password" \       # Required: SMTP password
    --date 2025-11-03 \                         # Specific date (default: yesterday)
    --attach-data                               # Attach compressed files (optional)
```

## Environment Variables

Instead of command-line flags, you can set:

```bash
export PAX_SMTP_PASSWORD="your-app-password"
```

Or create `~/.pax_email_creds`:

```bash
PAX_EMAIL_TO=your.email@gmail.com
PAX_SMTP_HOST=smtp.gmail.com
PAX_SMTP_PORT=587
PAX_SMTP_PASSWORD=your-app-password
```

Then in your cron job:

```bash
0 0 * * * source ~/.pax_email_creds && cd ~/pax && source venv/bin/activate && python -m pax.scripts.daily_export --email $PAX_EMAIL_TO --smtp-password $PAX_SMTP_PASSWORD >> ~/.pax_email.log 2>&1
```

## Email Content

The daily email includes:

```
Subject: Pax NYC Daily Data Export - 2025-11-03

Pax NYC Data Collection Report

Date: 2025-11-03

Summary:
- Metadata files: 40
- Images captured: 0
- Unique cameras: 40
- Warehouse parquet: Yes
- Parquet size: 0.05 MB
- Parquet path: /Users/gilraitses/pax/data/warehouse/snapshots/2025-11-03.parquet

Data files available on server:
  - /Users/gilraitses/pax/data/raw/metadata
  - /Users/gilraitses/pax/data/raw/images
  - /Users/gilraitses/pax/data/warehouse/snapshots

Dashboard: http://localhost:8000 (when running)

To download manually:
  cd ~/pax
  tar -czf pax_data_2025-11-03.tar.gz data/warehouse/snapshots/2025-11-03.parquet
```

## With Data Attachment

If you use `--attach-data`:
- Creates `data/exports/pax_data_YYYY-MM-DD.tar.gz`
- Includes warehouse parquet + batch metadata
- Attaches to email (may be large)

**Warning:** Email attachments have size limits:
- Gmail: 25 MB limit
- Most providers: 10-25 MB limit
- Use only if daily data is small

## Troubleshooting

### Email not sending

Check the log:
```bash
tail -f ~/.pax_email.log
```

Common issues:
1. **Invalid password**: Use app-specific password for Gmail
2. **SMTP blocked**: Check firewall, enable "Less secure apps" (not recommended)
3. **Wrong SMTP settings**: Verify host/port for your provider

### Test without cron

```bash
cd ~/pax
source venv/bin/activate
python -m pax.scripts.daily_export --email test@example.com --smtp-password "test"
```

Should show error or send email.

### Cron not running

Check cron is active:
```bash
crontab -l  # List jobs
ps aux | grep cron  # Check cron daemon
```

Check cron log:
```bash
grep CRON /var/log/system.log  # macOS
```

## Schedule Options

Change the cron schedule (first 5 fields):

```
# Every day at midnight
0 0 * * * /path/to/script

# Every day at 1:30 AM
30 1 * * * /path/to/script

# Every Monday at 9 AM
0 9 * * 1 /path/to/script

# Twice daily: midnight and noon
0 0,12 * * * /path/to/script
```

## Alternative: Manual Download

If email doesn't work, download manually:

```bash
cd ~/pax

# Compress today's data
DATE=$(date -v-1d +%Y-%m-%d)  # Yesterday
tar -czf "pax_data_$DATE.tar.gz" \
    "data/warehouse/snapshots/$DATE.parquet" \
    data/raw/metadata/batch_*.json

# Download via scp (if on remote server)
scp user@server:~/pax/pax_data_$DATE.tar.gz .
```

## Disable Email

Remove from crontab:

```bash
crontab -e
# Delete the line with pax_midnight_email
```

Or disable temporarily:

```bash
crontab -e
# Add # at the start of the line:
# 0 0 * * * /path/to/script
```

## Security Notes

1. **Protect credentials**: `chmod 600 ~/.pax_email_creds`
2. **Use app passwords**: Never use your main account password
3. **Limit cron access**: Cron jobs run with your user permissions
4. **Review logs**: Check `~/.pax_email.log` regularly

## Questions?

- Test script: `python -m pax.scripts.daily_export --help`
- Check logs: `tail -f ~/.pax_email.log`
- View cron: `crontab -l`

