#!/bin/bash

# BirdCam AI Processor Service Installation Script
# This script installs the ai-processor systemd service

set -e  # Exit on error

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "This script must be run with sudo"
    echo "Usage: sudo $0"
    exit 1
fi

echo "================================================"
echo "BirdCam AI Processor Service Installation"
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
SERVICE_FILE="$PROJECT_ROOT/systemd/ai-processor.service"
if [ ! -f "$SERVICE_FILE" ]; then
    echo "Error: Service file not found at $SERVICE_FILE"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "$PROJECT_ROOT/.venv" ]; then
    echo "Error: Virtual environment not found at $PROJECT_ROOT/.venv"
    echo "Please create a virtual environment and install dependencies first:"
    echo "  python3 -m venv .venv"
    echo "  source .venv/bin/activate"
    echo "  pip install -r requirements.processor.txt"
    exit 1
fi

# Check if .env.processor exists
if [ ! -f "$PROJECT_ROOT/.env.processor" ]; then
    echo "Error: Configuration file .env.processor not found"
    echo "Please create it from the example:"
    echo "  cp config/examples/.env.processor.example .env.processor"
    echo "  nano .env.processor"
    exit 1
fi

# Check if the web UI is built
if [ ! -d "$PROJECT_ROOT/web-ui/dist" ]; then
    echo "Warning: Web UI distribution not found at $PROJECT_ROOT/web-ui/dist"
    echo "The web interface will not be available until you build it:"
    echo "  cd web-ui"
    echo "  npm install"
    echo "  npm run build"
    echo
    read -p "Continue anyway? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create a temporary service file with correct paths
TEMP_SERVICE="/tmp/ai-processor.service"
echo "Creating service file with correct paths..."

cat > "$TEMP_SERVICE" << EOF
[Unit]
Description=BirdCam AI Processor Service
After=network.target

[Service]
Type=simple
User=$SUDO_USER
Group=$SUDO_USER
WorkingDirectory=$PROJECT_ROOT
Environment="PATH=$PROJECT_ROOT/.venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=$PROJECT_ROOT"
ExecStart=$PROJECT_ROOT/.venv/bin/python $PROJECT_ROOT/ai_processor/main.py
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ai-processor

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

# Allow network access
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
PrivateDevices=false

# For GPU access (if using CUDA)
SupplementaryGroups=video render

[Install]
WantedBy=multi-user.target
EOF

# Copy service file to systemd directory
echo "Installing service file..."
cp "$TEMP_SERVICE" /etc/systemd/system/ai-processor.service
rm "$TEMP_SERVICE"

# Create required directories with correct permissions
echo "Creating required directories..."
mkdir -p /var/birdcam/videos
mkdir -p /var/birdcam/processing
mkdir -p /var/birdcam/detections
mkdir -p /var/log/birdcam
chown -R $SUDO_USER:$SUDO_USER /var/birdcam
chown -R $SUDO_USER:$SUDO_USER /var/log/birdcam

# Create log rotation config
echo "Setting up log rotation..."
cat > /etc/logrotate.d/birdcam-ai << EOF
/var/log/birdcam/ai-processor.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 $SUDO_USER $SUDO_USER
    sharedscripts
    postrotate
        systemctl reload ai-processor.service > /dev/null 2>&1 || true
    endscript
}
EOF

# Check for NVIDIA GPU and CUDA
echo "Checking for GPU support..."
if command -v nvidia-smi &> /dev/null; then
    echo "✓ NVIDIA GPU detected"
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
    
    # Add CUDA paths to service if available
    if [ -d "/usr/local/cuda" ]; then
        echo "✓ CUDA installation found"
        sed -i '/Environment="PATH=/s/"$/:\/usr\/local\/cuda\/bin"/' /etc/systemd/system/ai-processor.service
        echo 'Environment="LD_LIBRARY_PATH=/usr/local/cuda/lib64"' >> /etc/systemd/system/ai-processor.service
    fi
else
    echo "ℹ No NVIDIA GPU detected - will use CPU for inference"
fi

# Reload systemd daemon
echo "Reloading systemd daemon..."
systemctl daemon-reload

# Enable service
echo "Enabling service..."
systemctl enable ai-processor.service

echo
echo "================================================"
echo "Service installation complete!"
echo "================================================"
echo
echo "The ai-processor service has been installed and enabled."
echo
echo "Available commands:"
echo "  Start service:   sudo systemctl start ai-processor"
echo "  Stop service:    sudo systemctl stop ai-processor"
echo "  Restart service: sudo systemctl restart ai-processor"
echo "  Check status:    sudo systemctl status ai-processor"
echo "  View logs:       sudo journalctl -u ai-processor -f"
echo
echo "The service will start automatically on boot."
echo
echo "Before starting the service, make sure to:"
echo "1. Configure .env.processor with your settings"
echo "2. Build the web UI (cd web-ui && npm run build)"
echo "3. Download AI models (they will auto-download on first run)"
echo
echo "To start the service now, run:"
echo "  sudo systemctl start ai-processor"
echo
echo "The web interface will be available at:"
echo "  http://localhost:5001"
echo
echo "================================================"