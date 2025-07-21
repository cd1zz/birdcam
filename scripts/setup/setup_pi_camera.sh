#!/bin/bash
# setup_pi_camera.sh - Automated Pi Camera setup for bird detection system

set -e  # Exit on any error

echo "🐦 Setting up Pi Camera for Bird Detection System..."

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo; then
    echo "⚠️  Warning: This script is designed for Raspberry Pi"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Enable camera interface
echo "📷 Enabling camera interface..."

# Check for boot config in multiple possible locations
BOOT_CONFIG=""
if [ -f "/boot/firmware/config.txt" ]; then
    BOOT_CONFIG="/boot/firmware/config.txt"
    echo "Found boot config at /boot/firmware/config.txt"
elif [ -f "/boot/config.txt" ]; then
    BOOT_CONFIG="/boot/config.txt"
    echo "Found boot config at /boot/config.txt"
else
    echo "⚠️  Warning: Could not find boot config file"
    echo "   Please manually enable camera in raspi-config"
fi

if [ -n "$BOOT_CONFIG" ]; then
    if ! grep -q "camera_auto_detect=1" "$BOOT_CONFIG"; then
        echo "Adding camera_auto_detect=1 to $BOOT_CONFIG"
        echo "camera_auto_detect=1" | sudo tee -a "$BOOT_CONFIG"
        REBOOT_REQUIRED=1
    fi
    
    # Add GPU memory configuration for better camera performance
    if ! grep -q "gpu_mem=" "$BOOT_CONFIG"; then
        echo "Adding gpu_mem=128 to $BOOT_CONFIG for better camera performance"
        echo "gpu_mem=128" | sudo tee -a "$BOOT_CONFIG"
        REBOOT_REQUIRED=1
    fi
fi

# Install system dependencies
echo "📦 Installing system dependencies..."
sudo apt update
sudo apt install -y python3-picamera2 libcamera-apps libcamera-dev python3-venv ffmpeg libopencv-dev python3-dev

# Add user to video group for camera permissions
echo "🔐 Adding user to video group for camera permissions..."
sudo usermod -a -G video $USER
echo "✅ User $USER added to video group"

# Check if venv exists and has system packages
if [ -d ".venv" ]; then
    echo "🔍 Checking existing virtual environment..."
    
    # Test if current venv can import picamera2
    if .venv/bin/python -c "import picamera2" 2>/dev/null; then
        echo "✅ Virtual environment already has picamera2 access"
    else
        echo "🔄 Recreating virtual environment with system packages access..."
        rm -rf .venv
        python3 -m venv .venv --system-site-packages
        echo "✅ Virtual environment recreated"
    fi
else
    echo "🆕 Creating virtual environment with system packages access..."
    python3 -m venv .venv --system-site-packages
fi

# Activate venv and install requirements
echo "📋 Installing Python requirements..."
source .venv/bin/activate

# Remove picamera2 from requirements if it exists
if grep -q "picamera2" requirements.txt; then
    echo "🔧 Installing requirements without picamera2 (using system version)"
    grep -v "picamera2" requirements.txt > /tmp/requirements_no_picamera2.txt
    pip install -r /tmp/requirements_no_picamera2.txt
else
    pip install -r requirements.txt
fi

# Test camera
echo "🧪 Testing camera..."
if python3 -c "from picamera2 import Picamera2; cameras = Picamera2.global_camera_info(); print(f'Found {len(cameras)} camera(s): {cameras}'); assert len(cameras) > 0" 2>/dev/null; then
    echo "✅ Camera test successful!"
else
    echo "❌ Camera test failed. Please check:"
    echo "   1. Camera is properly connected"
    echo "   2. Camera is enabled in raspi-config"
    echo "   3. Try rebooting if you just enabled the camera"
    exit 1
fi

# Create/update .env file
echo "⚙️  Configuring environment..."

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📋 Summary:"
echo "   ✅ System camera packages installed"
echo "   ✅ FFmpeg and OpenCV system libraries installed"
echo "   ✅ User added to video group for camera permissions"
echo "   ✅ Virtual environment configured with system access"
echo "   ✅ Python requirements installed"
echo "   ✅ Camera tested successfully"
echo "   ✅ Environment configured"
echo ""

if [ "$REBOOT_REQUIRED" = "1" ]; then
    echo "⚠️  REBOOT REQUIRED: Camera interface was just enabled"
    echo "   Please run: sudo reboot"
    echo "   Then start your service with: python3 pi_capture/main.py"
else
    echo "🚀 Ready to start! Run: python3 pi_capture/main.py"
fi

echo ""
echo "🔍 Note: If you added the user to the video group, you may need to"
echo "   log out and back in for permissions to take effect."