#!/bin/bash

# BirdCam Pi Capture Service Installation Script
# This script installs the pi-capture systemd service

set -e  # Exit on error

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "This script must be run with sudo"
    echo "Usage: sudo $0"
    exit 1
fi

echo "================================================"
echo "BirdCam Pi Capture Service Installation"
echo "================================================"
echo

# Get the script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Get the user who invoked sudo
SUDO_USER="${SUDO_USER:-$USER}"
if [ -z "$SUDO_USER" ] || [ "$SUDO_USER" = "root" ]; then
    echo "Error: Could not determine the non-root user."
    echo "Please run this script using: sudo -E $0"
    exit 1
fi

echo "Installing service for user: $SUDO_USER"
echo "Project root: $PROJECT_ROOT"

# Check if the service file exists
SERVICE_FILE="$PROJECT_ROOT/systemd/pi-capture.service"
if [ ! -f "$SERVICE_FILE" ]; then
    echo "Error: Service file not found at $SERVICE_FILE"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "$PROJECT_ROOT/.venv" ]; then
    echo "Error: Virtual environment not found at $PROJECT_ROOT/.venv"
    echo "Please run ./scripts/setup/setup_pi_camera.sh first"
    exit 1
fi

# Check if .env.pi exists
if [ ! -f "$PROJECT_ROOT/.env.pi" ]; then
    echo "Error: Configuration file .env.pi not found"
    echo "Please run python scripts/setup/pi_env_generator.py first"
    exit 1
fi

# Create a temporary service file with correct paths
TEMP_SERVICE="/tmp/pi-capture.service"
echo "Creating service file with correct paths..."

cat > "$TEMP_SERVICE" << EOF
[Unit]
Description=BirdCam Pi Capture Service
After=network.target

[Service]
Type=simple
User=$SUDO_USER
Group=$SUDO_USER
WorkingDirectory=$PROJECT_ROOT
Environment="PATH=$PROJECT_ROOT/.venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=$PROJECT_ROOT"
ExecStart=$PROJECT_ROOT/.venv/bin/python $PROJECT_ROOT/pi_capture/main.py
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=pi-capture

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/birdcam /var/log/birdcam $PROJECT_ROOT
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictRealtime=true
RestrictSUIDSGID=true

# Device access for cameras
DeviceAllow=/dev/video* rw
DeviceAllow=/dev/vchiq rw
DeviceAllow=/dev/vcsm-cma rw
DeviceAllow=/dev/dma_heap/* rw
SupplementaryGroups=video

[Install]
WantedBy=multi-user.target
EOF

# Copy service file to systemd directory
echo "Installing service file..."
cp "$TEMP_SERVICE" /etc/systemd/system/pi-capture.service
rm "$TEMP_SERVICE"

# Create required directories with correct permissions
echo "Creating required directories..."
mkdir -p /var/birdcam/videos
mkdir -p /var/log/birdcam
chown -R $SUDO_USER:$SUDO_USER /var/birdcam
chown -R $SUDO_USER:$SUDO_USER /var/log/birdcam

# Create log rotation config
echo "Setting up log rotation..."
cat > /etc/logrotate.d/birdcam << EOF
/var/log/birdcam/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 $SUDO_USER $SUDO_USER
    sharedscripts
    postrotate
        systemctl reload pi-capture.service > /dev/null 2>&1 || true
    endscript
}
EOF

# Reload systemd daemon
echo "Reloading systemd daemon..."
systemctl daemon-reload

# Enable service
echo "Enabling service..."
systemctl enable pi-capture.service

echo
echo "================================================"
echo "Service installation complete!"
echo "================================================"
echo
echo "The pi-capture service has been installed and enabled."
echo
echo "Available commands:"
echo "  Start service:   sudo systemctl start pi-capture"
echo "  Stop service:    sudo systemctl stop pi-capture"
echo "  Restart service: sudo systemctl restart pi-capture"
echo "  Check status:    sudo systemctl status pi-capture"
echo "  View logs:       sudo journalctl -u pi-capture -f"
echo
echo "The service will start automatically on boot."
echo
echo "To start the service now, run:"
echo "  sudo systemctl start pi-capture"
echo
echo "================================================"