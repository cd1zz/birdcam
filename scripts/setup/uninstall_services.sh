#!/bin/bash
# Uninstall script for Birdcam systemd services

set -e

echo "[INFO] Uninstalling Birdcam Services..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "[ERROR] Please run as root (use sudo)"
    exit 1
fi

# Function to uninstall a service
uninstall_service() {
    local service_name=$1
    
    if systemctl is-active --quiet "$service_name"; then
        echo "[INFO] Stopping $service_name..."
        systemctl stop "$service_name"
    fi
    
    if systemctl is-enabled --quiet "$service_name" 2>/dev/null; then
        echo "[INFO] Disabling $service_name..."
        systemctl disable "$service_name"
    fi
    
    if [ -f "/etc/systemd/system/$service_name" ]; then
        echo "[INFO] Removing $service_name..."
        rm -f "/etc/systemd/system/$service_name"
    fi
}

# Uninstall services
uninstall_service "ai-processor.service"
uninstall_service "pi-capture.service"

# Reload systemd
echo "[INFO] Reloading systemd..."
systemctl daemon-reload

echo "[SUCCESS] Services uninstalled successfully!"
echo ""
echo "Note: This script only removes the systemd service files."
echo "Your data, configuration, and application files remain intact."