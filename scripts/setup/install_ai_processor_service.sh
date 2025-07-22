#!/bin/bash
# Installation script for AI Processor systemd service

set -e

echo "[INFO] Installing Birdcam AI Processor Service..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "[ERROR] Please run as root (use sudo)"
    exit 1
fi

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if service file exists
if [ ! -f "$SCRIPT_DIR/systemd/ai-processor.service" ]; then
    echo "[ERROR] Service file not found at $SCRIPT_DIR/systemd/ai-processor.service"
    exit 1
fi

# Get the actual user who ran sudo
ACTUAL_USER="${SUDO_USER:-$USER}"
ACTUAL_HOME=$(getent passwd "$ACTUAL_USER" | cut -d: -f6)

# Update the service file with correct paths and user
echo "[INFO] Configuring service for user: $ACTUAL_USER"
sed "s|/home/craig|$ACTUAL_HOME|g; s|User=craig|User=$ACTUAL_USER|g; s|Group=craig|Group=$ACTUAL_USER|g" \
    "$SCRIPT_DIR/systemd/ai-processor.service" > /tmp/ai-processor.service

# Copy service file to systemd directory
echo "[INFO] Installing service file..."
cp /tmp/ai-processor.service /etc/systemd/system/
rm /tmp/ai-processor.service

# Create necessary directories
echo "[INFO] Creating directories..."
sudo -u "$ACTUAL_USER" mkdir -p "$ACTUAL_HOME/birdcam/storage/uploads"
sudo -u "$ACTUAL_USER" mkdir -p "$ACTUAL_HOME/birdcam/storage/processed"
sudo -u "$ACTUAL_USER" mkdir -p "$ACTUAL_HOME/birdcam/storage/detected"
sudo -u "$ACTUAL_USER" mkdir -p "$ACTUAL_HOME/birdcam/storage/thumbnails"
sudo -u "$ACTUAL_USER" mkdir -p "$ACTUAL_HOME/birdcam/database"

# Add user to systemd-journal group for log access
echo "[INFO] Adding user to systemd-journal group..."
usermod -a -G systemd-journal "$ACTUAL_USER" 2>/dev/null || true

# Reload systemd
echo "[INFO] Reloading systemd..."
systemctl daemon-reload

# Enable the service
echo "[INFO] Enabling service..."
systemctl enable ai-processor.service

echo "[SUCCESS] AI Processor service installed successfully!"
echo ""
echo "To start the service:"
echo "  sudo systemctl start ai-processor.service"
echo ""
echo "To check status:"
echo "  sudo systemctl status ai-processor.service"
echo ""
echo "To view logs:"
echo "  journalctl -u ai-processor.service -f"
echo ""
echo "Note: Make sure you have:"
echo "  1. Created and activated the Python virtual environment"
echo "  2. Installed all requirements: pip install -r requirements.processor.txt"
echo "  3. Configured .env file with proper settings"