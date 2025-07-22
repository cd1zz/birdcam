#!/bin/bash
# Installation script for Pi Capture systemd service (run on Raspberry Pi)

set -e

echo "[INFO] Installing Birdcam Pi Capture Service..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "[ERROR] Please run as root (use sudo)"
    exit 1
fi

# Check if this is a Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo "[WARNING] This doesn't appear to be a Raspberry Pi. Continue anyway? (y/n)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if service file exists
if [ ! -f "$SCRIPT_DIR/systemd/pi-capture.service" ]; then
    echo "[ERROR] Service file not found at $SCRIPT_DIR/systemd/pi-capture.service"
    exit 1
fi

# Get the actual user who ran sudo
ACTUAL_USER="${SUDO_USER:-pi}"
ACTUAL_HOME=$(getent passwd "$ACTUAL_USER" | cut -d: -f6)

# Update the service file with correct paths and user
echo "[INFO] Configuring service for user: $ACTUAL_USER"
sed "s|/home/pi|$ACTUAL_HOME|g; s|User=pi|User=$ACTUAL_USER|g; s|Group=pi|Group=$ACTUAL_USER|g" \
    "$SCRIPT_DIR/systemd/pi-capture.service" > /tmp/pi-capture.service

# Copy service file to systemd directory
echo "[INFO] Installing service file..."
cp /tmp/pi-capture.service /etc/systemd/system/
rm /tmp/pi-capture.service

# Create necessary directories
echo "[INFO] Creating directories..."
sudo -u "$ACTUAL_USER" mkdir -p "$ACTUAL_HOME/birdcam/storage/segments"
sudo -u "$ACTUAL_USER" mkdir -p "$ACTUAL_HOME/birdcam/storage/synced"
sudo -u "$ACTUAL_USER" mkdir -p "$ACTUAL_HOME/birdcam/database"

# Add user to necessary groups
echo "[INFO] Adding user to video and systemd-journal groups..."
usermod -a -G video "$ACTUAL_USER" 2>/dev/null || true
usermod -a -G systemd-journal "$ACTUAL_USER" 2>/dev/null || true

# Enable camera if not already enabled
if ! vcgencmd get_camera | grep -q "detected=1"; then
    echo "[INFO] Enabling camera..."
    # For newer Raspberry Pi OS versions
    if [ -f /boot/config.txt ]; then
        if ! grep -q "^camera_auto_detect=1" /boot/config.txt; then
            echo "camera_auto_detect=1" >> /boot/config.txt
        fi
    elif [ -f /boot/firmware/config.txt ]; then
        if ! grep -q "^camera_auto_detect=1" /boot/firmware/config.txt; then
            echo "camera_auto_detect=1" >> /boot/firmware/config.txt
        fi
    fi
    echo "[WARNING] Camera configuration updated. A reboot may be required."
fi

# Reload systemd
echo "[INFO] Reloading systemd..."
systemctl daemon-reload

# Enable the service
echo "[INFO] Enabling service..."
systemctl enable pi-capture.service

echo "[SUCCESS] Pi Capture service installed successfully!"
echo ""
echo "To start the service:"
echo "  sudo systemctl start pi-capture.service"
echo ""
echo "To check status:"
echo "  sudo systemctl status pi-capture.service"
echo ""
echo "To view logs:"
echo "  journalctl -u pi-capture.service -f"
echo ""
echo "Note: Make sure you have:"
echo "  1. Created and activated the Python virtual environment"
echo "  2. Installed all requirements: pip install -r requirements.capture.txt"
echo "  3. Configured .env file with proper settings"
echo "  4. Connected and tested your camera(s)"
echo ""
if ! vcgencmd get_camera 2>/dev/null | grep -q "detected=1"; then
    echo "[IMPORTANT] Camera not detected. Please reboot if you just enabled it."
fi