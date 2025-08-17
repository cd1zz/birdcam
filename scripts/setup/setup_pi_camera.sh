#!/bin/bash

# BirdCam Raspberry Pi Camera Setup Script
# This script sets up the Python environment for the Pi camera capture system
# It handles the complex picamera2/numpy/venv issues automatically

set -e  # Exit on error

echo "================================================"
echo "BirdCam Raspberry Pi Camera Setup"
echo "================================================"
echo

# Check if running with sudo
if [ "$EUID" -eq 0 ]; then 
    echo "Error: This script should not be run with sudo"
    echo "Please run as: ./setup_pi_camera.sh"
    echo
    echo "The script will ask for sudo when needed for system directories."
    exit 1
fi

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ]; then
    echo "Warning: This doesn't appear to be a Raspberry Pi."
    read -p "Continue anyway? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check for basic Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not found"
    echo "Please install it with: sudo apt install python3"
    exit 1
fi

# Get the project root (two levels up from this script)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
cd "$PROJECT_ROOT"

echo "Project root: $PROJECT_ROOT"

# Check if virtual environment already exists
if [ -d ".venv" ]; then
    echo
    echo "Virtual environment already exists."
    read -p "Delete and recreate? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing existing virtual environment..."
        rm -rf .venv
    else
        echo "Keeping existing virtual environment."
        echo
        echo "To activate it, run: source .venv/bin/activate"
        echo "To test picamera2, run: python3 -c \"from picamera2 import Picamera2; print('picamera2 working')\""
        exit 0
    fi
fi

# Install all required system packages
echo
echo "Installing system dependencies..."
echo "This may take a few minutes and requires sudo access."

sudo apt update

# Install core Python and camera packages
sudo apt install -y \
    python3-picamera2 \
    python3-libcamera \
    python3-kms++ \
    python3-numpy \
    python3-opencv \
    python3-pip \
    python3-venv \
    python3-dev \
    libcamera-dev \
    libcamera-tools \
    v4l-utils

echo "✓ System packages installed"

# Verify picamera2 is available system-wide
echo
echo "Verifying picamera2 system installation..."
if python3 -c "import picamera2; from picamera2 import Picamera2; print('✓ picamera2 system installation verified')" 2>/dev/null; then
    echo "✓ picamera2 is properly installed"
else
    echo "✗ Error: picamera2 is not properly installed"
    echo "Please check the installation and try again"
    exit 1
fi

# Create virtual environment with system site packages
echo
echo "Creating virtual environment with system site packages..."
python3 -m venv --system-site-packages .venv

if [ ! -d ".venv" ]; then
    echo "Error: Failed to create virtual environment"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip in virtual environment
echo
echo "Upgrading pip..."
pip install --upgrade pip

# Verify picamera2 is accessible in venv
echo
echo "Verifying picamera2 access in virtual environment..."

# Test basic import (this is the key test - not the __version__ attribute)
if python3 -c "import picamera2; from picamera2 import Picamera2; print('✓ picamera2 is accessible in virtual environment')" 2>/dev/null; then
    echo "✓ picamera2 is working correctly"
    
    # Try to get version info, but don't fail if it's not available
    echo "Getting picamera2 info..."
    python3 -c "
import picamera2
try:
    print(f'  Version: {picamera2.__version__}')
except AttributeError:
    print('  Version: Information not available (normal for some versions)')
print(f'  Location: {picamera2.__file__}')
print(f'  Available classes: {[x for x in dir(picamera2) if not x.startswith(\"_\")][0:5]}...')
" 2>/dev/null || echo "  Basic info retrieved"
    
else
    echo "✗ Error: picamera2 is not accessible in the virtual environment"
    echo
    echo "Attempting to fix with manual path addition..."
    
    # Add system packages path manually
    echo "/usr/lib/python3/dist-packages" > .venv/lib/python3.11/site-packages/system-packages.pth
    
    # Test again
    if python3 -c "import picamera2; from picamera2 import Picamera2; print('✓ Manual fix successful')" 2>/dev/null; then
        echo "✓ picamera2 is now accessible"
    else
        echo "✗ Manual fix failed"
        echo
        echo "This might be due to:"
        echo "1. Python version mismatch between system and venv"
        echo "2. Corrupted picamera2 installation"
        echo "3. Missing system dependencies"
        echo
        echo "Troubleshooting steps:"
        echo "1. Try: sudo apt reinstall python3-picamera2"
        echo "2. Check Python version compatibility"
        echo "3. Verify camera is connected and enabled in raspi-config"
        exit 1
    fi
fi

# Verify numpy compatibility
echo
echo "Checking numpy compatibility..."
if python3 -c "import numpy; import picamera2; print('✓ numpy version:', numpy.__version__)" 2>/dev/null; then
    echo "✓ numpy and picamera2 are compatible"
else
    echo "⚠ Warning: There might be numpy compatibility issues"
    echo "The system will use the system numpy installation"
fi

# Add user to video group for camera access
echo
echo "Setting up camera permissions..."
if groups $USER | grep -q '\bvideo\b'; then
    echo "✓ User $USER is already in video group"
else
    echo "Adding user $USER to video group (requires sudo)..."
    sudo usermod -a -G video $USER
    echo "✓ User added to video group"
    echo "⚠ You may need to log out and back in for camera permissions to take effect"
fi

# Create required directories
echo
echo "Creating required directories..."

# Check if directories exist and create them with sudo if needed
if [ ! -d /var/birdcam ]; then
    echo "Creating /var/birdcam directory (requires sudo)..."
    sudo mkdir -p /var/birdcam/videos
    sudo chown -R $USER:$USER /var/birdcam
else
    # Directory exists, ensure subdirectories exist
    if [ ! -d /var/birdcam/videos ]; then
        mkdir -p /var/birdcam/videos
    fi
fi

if [ ! -d /var/log/birdcam ]; then
    echo "Creating /var/log/birdcam directory (requires sudo)..."
    sudo mkdir -p /var/log/birdcam
    sudo chown -R $USER:$USER /var/log/birdcam
fi

echo "✓ Directories created with proper permissions"

# Test camera detection (optional)
echo
echo "Testing camera detection..."
echo "CSI Cameras:"
if command -v rpicam-hello &> /dev/null; then
    rpicam-hello --list-cameras 2>/dev/null | head -10 || echo "  No CSI cameras detected or not accessible"
elif command -v libcamera-hello &> /dev/null; then
    libcamera-hello --list-cameras 2>/dev/null | head -10 || echo "  No CSI cameras detected or not accessible"
else
    echo "  Camera detection tools not available"
fi

echo "USB Cameras:"
if command -v v4l2-ctl &> /dev/null; then
    v4l2-ctl --list-devices 2>/dev/null | head -10 || echo "  No USB cameras detected"
else
    echo "  v4l2-ctl not available for USB camera detection"
fi

echo
echo "================================================"
echo "Setup complete!"
echo "================================================"
echo
echo "✓ Virtual environment created with system package access"
echo "✓ picamera2 is working in the virtual environment"
echo "✓ Required directories created"
echo "✓ Camera permissions configured"
echo
echo "Next steps:"
echo "1. Activate the virtual environment:"
echo "   source .venv/bin/activate"
echo
echo "2. Install Python dependencies:"
echo "   pip install -r requirements.capture.txt"
echo
echo "3. Configure your cameras:"
echo "   python scripts/setup/pi_env_generator.py"
echo
echo "4. Test the camera system:"
echo "   python pi_capture/main.py"
echo
echo "5. Install as a service:"
echo "   sudo ./scripts/setup/install_pi_capture_service.sh"
echo
echo "================================================"

# Final reminder about reboot if needed
if ! groups $USER | grep -q '\bvideo\b'; then
    echo
    echo "⚠ IMPORTANT: You may need to reboot or log out/in for camera"
    echo "permissions to take effect if you encounter permission errors."
fi

echo
echo "Remember: Always activate the virtual environment before running:"
echo "source .venv/bin/activate"
