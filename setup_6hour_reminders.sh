#!/usr/bin/env bash
# Setup 6-hour email reminders for GCS data downloads

set -e

echo "Pax NYC - 6-Hour Download Reminders Setup"
echo "==========================================="
echo ""

# Get user email
read -p "Enter your email address: " USER_EMAIL

# Get SMTP settings
echo ""
echo "Email Provider Setup:"
echo "1. Gmail (smtp.gmail.com)"
echo "2. Outlook (smtp.office365.com)"
echo "3. Custom SMTP server"
read -p "Choose provider (1-3): " PROVIDER_CHOICE

case "$PROVIDER_CHOICE" in
    1)
        SMTP_HOST="smtp.gmail.com"
        SMTP_PORT=587
        echo ""
        echo "Gmail Setup:"
        echo "1. Go to https://myaccount.google.com/apppasswords"
        echo "2. Create an 'App Password' for 'Pax NYC Download Reminders'"
        echo "3. Copy the 16-character password"
        ;;
    2)
        SMTP_HOST="smtp.office365.com"
        SMTP_PORT=587
        ;;
    3)
        read -p "SMTP host: " SMTP_HOST
        read -p "SMTP port: " SMTP_PORT
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
read -s -p "Enter SMTP password (or app password): " SMTP_PASSWORD
echo ""

# Create credentials file
CREDS_FILE="$HOME/.pax_download_reminder_creds"
cat > "$CREDS_FILE" << EOF
PAX_EMAIL_TO=$USER_EMAIL
PAX_SMTP_HOST=$SMTP_HOST
PAX_SMTP_PORT=$SMTP_PORT
PAX_SMTP_USER=$USER_EMAIL
PAX_SMTP_PASSWORD=$SMTP_PASSWORD
EOF

chmod 600 "$CREDS_FILE"

# Create wrapper script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WRAPPER_SCRIPT="$HOME/.pax_6hour_reminder.sh"

cat > "$WRAPPER_SCRIPT" << EOF
#!/usr/bin/env bash
# Pax 6-hour download reminder wrapper (auto-generated)

source "$CREDS_FILE"
export PATH="/opt/homebrew/share/google-cloud-sdk/bin:\$PATH"
export CLOUDSDK_PYTHON=\$(which python3)
cd "$SCRIPT_DIR"
source venv/bin/activate

python -m pax.scripts.email_download_reminder \\
    --email "\$PAX_EMAIL_TO" \\
    --smtp-host "\$PAX_SMTP_HOST" \\
    --smtp-port "\$PAX_SMTP_PORT" \\
    --smtp-user "\$PAX_SMTP_USER" \\
    --smtp-password "\$PAX_SMTP_PASSWORD" \\
    --hours 6 \\
    >> "$HOME/.pax_download_reminder.log" 2>&1
EOF

chmod +x "$WRAPPER_SCRIPT"

# Setup cron job
echo ""
echo "Setting up cron job for 6-hour reminders..."

# Create cron entries (every 6 hours: 00:00, 06:00, 12:00, 18:00)
CRON_ENTRIES="0 0,6,12,18 * * * $WRAPPER_SCRIPT"

# Check if entry already exists
if crontab -l 2>/dev/null | grep -q "pax_6hour_reminder"; then
    echo "Cron job already exists. Updating..."
    crontab -l | grep -v "pax_6hour_reminder" | crontab -
fi

# Add new entries
(crontab -l 2>/dev/null; echo "# Pax 6-hour download reminders"; echo "$CRON_ENTRIES") | crontab -

echo ""
echo "Setup complete!"
echo ""
echo "Configuration saved to: $CREDS_FILE"
echo "Wrapper script: $WRAPPER_SCRIPT"
echo "Log file: $HOME/.pax_download_reminder.log"
echo ""
echo "Schedule: Every 6 hours (00:00, 06:00, 12:00, 18:00)"
echo ""
echo "To test immediately:"
echo "  $WRAPPER_SCRIPT"
echo ""
echo "To view cron jobs:"
echo "  crontab -l"
echo ""

