#!/usr/bin/env bash
# Setup midnight email notifications for Pax data collection

set -e

echo "Pax NYC - Midnight Email Notification Setup"
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
        echo "2. Create an 'App Password' for 'Pax NYC'"
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

# Optional: attach data
echo ""
read -p "Attach data files to email? (may be large) [y/N]: " ATTACH_DATA
if [[ "$ATTACH_DATA" =~ ^[Yy]$ ]]; then
    ATTACH_FLAG="--attach-data"
else
    ATTACH_FLAG=""
fi

# Create credentials file
CREDS_FILE="$HOME/.pax_email_creds"
cat > "$CREDS_FILE" << EOF
PAX_EMAIL_TO=$USER_EMAIL
PAX_SMTP_HOST=$SMTP_HOST
PAX_SMTP_PORT=$SMTP_PORT
PAX_SMTP_USER=$USER_EMAIL
PAX_SMTP_PASSWORD=$SMTP_PASSWORD
PAX_ATTACH_DATA=$ATTACH_FLAG
EOF

chmod 600 "$CREDS_FILE"

# Create wrapper script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WRAPPER_SCRIPT="$HOME/.pax_midnight_email.sh"

cat > "$WRAPPER_SCRIPT" << EOF
#!/usr/bin/env bash
# Pax midnight email wrapper (auto-generated)

source "$CREDS_FILE"
cd "$SCRIPT_DIR"
source venv/bin/activate

python -m pax.scripts.daily_export \\
    --email "\$PAX_EMAIL_TO" \\
    --smtp-host "\$PAX_SMTP_HOST" \\
    --smtp-port "\$PAX_SMTP_PORT" \\
    --smtp-user "\$PAX_SMTP_USER" \\
    --smtp-password "\$PAX_SMTP_PASSWORD" \\
    \$PAX_ATTACH_DATA \\
    >> "$HOME/.pax_email.log" 2>&1
EOF

chmod +x "$WRAPPER_SCRIPT"

# Setup cron job
echo ""
echo "Setting up cron job for midnight execution..."

# Create cron entry
CRON_ENTRY="0 0 * * * $WRAPPER_SCRIPT"

# Check if entry already exists
if crontab -l 2>/dev/null | grep -q "pax_midnight_email"; then
    echo "Cron job already exists. Updating..."
    crontab -l | grep -v "pax_midnight_email" | crontab -
fi

# Add new entry
(crontab -l 2>/dev/null; echo "# Pax midnight email notification"; echo "$CRON_ENTRY") | crontab -

echo ""
echo "Setup complete!"
echo ""
echo "Configuration saved to: $CREDS_FILE"
echo "Wrapper script: $WRAPPER_SCRIPT"
echo "Log file: $HOME/.pax_email.log"
echo ""
echo "Cron schedule: Every day at midnight (00:00)"
echo ""
echo "To test immediately:"
echo "  $WRAPPER_SCRIPT"
echo ""
echo "To view cron jobs:"
echo "  crontab -l"
echo ""
echo "To disable:"
echo "  crontab -e  # Remove the 'pax_midnight_email' line"
echo ""

