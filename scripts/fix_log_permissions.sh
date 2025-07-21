#!/bin/bash
# Script to fix permissions for remote log access

echo "Fixing permissions for remote log access..."

# Create the remote log directory if it doesn't exist
if [ ! -d "/var/log/remote" ]; then
    echo "Creating /var/log/remote directory..."
    sudo mkdir -p /var/log/remote
fi

# Set ownership to syslog user
echo "Setting ownership to syslog:adm..."
sudo chown -R syslog:adm /var/log/remote

# Set permissions to allow group read access
echo "Setting permissions..."
sudo chmod -R 750 /var/log/remote

# Get the web server user
WEB_USER=$(ps aux | grep -E 'python.*ai_processor/main.py|gunicorn|uwsgi' | grep -v grep | awk '{print $1}' | head -n1)

if [ -z "$WEB_USER" ]; then
    echo "Could not detect web server user automatically."
    echo "Please run: sudo usermod -a -G adm YOUR_WEB_USER"
else
    echo "Detected web server user: $WEB_USER"
    echo "Adding $WEB_USER to adm group..."
    sudo usermod -a -G adm $WEB_USER
    echo ""
    echo "IMPORTANT: You need to restart the AI processor service for group changes to take effect:"
    echo "  sudo systemctl restart ai-processor.service"
fi

# Check current permissions
echo ""
echo "Current permissions:"
ls -la /var/log/remote/

echo ""
echo "Done! If you're still having permission issues:"
echo "1. Make sure rsyslog is configured and running"
echo "2. Check that remote logs are being received in /var/log/remote/"
echo "3. Restart the AI processor service"