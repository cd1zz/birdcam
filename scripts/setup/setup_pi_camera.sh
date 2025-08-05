#!/bin/bash

# BirdCam Raspberry Pi Camera Setup Script
# This script sets up the Python environment for the Pi camera capture system
# It handles the complex picamera2/numpy/venv issues automatically

set -e  # Exit on error

echo "================================================"
echo "BirdCam Raspberry Pi Camera Setup"
echo "================================================"
echo

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ]; then
    echo "Warning: This doesn't appear to be a Raspberry Pi."
    read -p "Continue anyway? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check for required system packages
echo "Checking system dependencies..."
MISSING_DEPS=()

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    MISSING_DEPS+=("python3")
fi

# Check for pip
if ! command -v pip3 &> /dev/null; then
    MISSING_DEPS+=("python3-pip")
fi

# Check for venv
if ! python3 -c "import venv" &> /dev/null; then
    MISSING_DEPS+=("python3-venv")
fi

# Check for libcamera/rpicam commands (rpicam-* is the new naming)
CAMERA_CMD_FOUND=false
for cmd in rpicam-hello rpicam-still rpicam-vid libcamera-hello libcamera-still libcamera-vid; do
    if command -v $cmd &> /dev/null; then
        CAMERA_CMD_FOUND=true
        break
    fi
done

if [ "$CAMERA_CMD_FOUND" = false ]; then
    # Also check if the packages are installed
    if ! dpkg -l rpicam-apps 2>/dev/null | grep -q "^ii" && \
       ! dpkg -l libcamera-apps 2>/dev/null | grep -q "^ii"; then
        MISSING_DEPS+=("rpicam-apps")
    fi
fi

# Check for v4l2 tools (for USB cameras)
if ! command -v v4l2-ctl &> /dev/null; then
    MISSING_DEPS+=("v4l-utils")
fi

if [ ${#MISSING_DEPS[@]} -ne 0 ]; then
    echo "Missing system dependencies: ${MISSING_DEPS[*]}"
    echo
    echo "Please install them with:"
    echo "sudo apt update"
    echo "sudo apt install -y ${MISSING_DEPS[*]}"
    exit 1
fi

# Check for picamera2 (system package)
echo
echo "Checking for picamera2..."
if ! python3 -c "import picamera2" &> /dev/null 2>&1; then
    echo "picamera2 is not installed as a system package."
    echo
    echo "Please install it with:"
    echo "sudo apt update"
    echo "sudo apt install -y python3-picamera2"
    echo
    echo "Note: picamera2 must be installed as a system package,"
    echo "not via pip, due to its integration with libcamera."
    exit 1
fi

echo "✓ picamera2 found"

# Get the project root (two levels up from this script)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
cd "$PROJECT_ROOT"

echo
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
        exit 0
    fi
fi

# Create virtual environment with system site packages
# This is CRITICAL for picamera2 to work properly
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

# Upgrade pip
echo
echo "Upgrading pip..."
pip install --upgrade pip

# Verify picamera2 is accessible in venv
echo
echo "Verifying picamera2 access in virtual environment..."
if python -c "import picamera2; print('✓ picamera2 version:', picamera2.__version__)" 2>/dev/null; then
    echo "✓ picamera2 is accessible"
else
    echo "✗ Error: picamera2 is not accessible in the virtual environment"
    echo "This usually means --system-site-packages flag didn't work properly"
    exit 1
fi

# Verify numpy compatibility
echo
echo "Checking numpy compatibility..."
if python -c "import numpy; import picamera2; print('✓ numpy version:', numpy.__version__)" 2>/dev/null; then
    echo "✓ numpy and picamera2 are compatible"
else
    echo "⚠ Warning: There might be numpy compatibility issues"
    echo "The system will attempt to use the system numpy"
fi

# Create required directories
echo
echo "Creating required directories..."
mkdir -p /var/birdcam/videos
mkdir -p /var/log/birdcam

# Set permissions (user needs to own these)
if [ -w /var/birdcam ]; then
    echo "Setting permissions on /var/birdcam..."
    sudo chown -R $USER:$USER /var/birdcam
    sudo chown -R $USER:$USER /var/log/birdcam
else
    echo "Note: You may need to run with sudo to create system directories"
fi

echo
echo "================================================"
echo "Setup complete!"
echo "================================================"
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

# Reminder about virtual environment
echo
echo "Remember: Always activate the virtual environment before running the capture system:"
echo "source .venv/bin/activate"
echo