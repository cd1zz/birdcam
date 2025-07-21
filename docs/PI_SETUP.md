# Raspberry Pi Setup Guide

Complete guide for setting up the camera capture system on Raspberry Pi.

## Hardware Requirements

- Raspberry Pi 4 or 5 (3B+ works but with limitations)
- At least one camera:
  - CSI camera (Raspberry Pi Camera v2/v3/HQ)
  - USB webcam (most Logitech models work well)
- 16GB+ SD card
- Stable network connection to processing server

## Software Requirements

- Raspberry Pi OS (64-bit recommended)
- Python 3.9 or higher
- Network access to your AI Processing Server

## Step 1: Initial Pi Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required system packages
sudo apt install -y \
    python3-pip \
    python3-venv \
    git \
    libcamera-apps \
    libcamera-dev \
    python3-picamera2 \
    libopencv-dev \
    python3-opencv

# Add user to video group
sudo usermod -a -G video $USER

# Reboot to apply changes
sudo reboot
```

## Step 2: Clone and Configure

```bash
# Clone the repository
git clone https://github.com/yourusername/birdcam.git
cd birdcam

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Pi-specific dependencies
pip install -r requirements.pi.txt

# Create configuration
cp config/examples/.env.pi.example .env.pi
nano .env.pi
```

## Step 3: Critical Configuration

Edit `.env.pi` with your network details:

```bash
# MOST IMPORTANT - Your AI server's IP address
PROCESSING_SERVER=192.168.1.100  # Change this!

# Camera configuration
CAMERA_IDS=0                     # Use 0 for single camera, 0,1 for dual

# Motion sensitivity (adjust after testing)
MOTION_THRESHOLD=5000            # Lower = more sensitive
MIN_CONTOUR_AREA=500            # Minimum motion size
```

## Step 4: Camera Setup

### For CSI Camera:
```bash
# Enable camera interface
sudo raspi-config
# Navigate to: Interface Options → Camera → Enable

# Test camera
libcamera-hello --list-cameras

# Run setup script
./scripts/setup/setup_pi_camera.sh
```

### For USB Camera:
```bash
# List USB cameras
ls /dev/video*

# Test camera (install if needed: sudo apt install v4l-utils)
v4l2-ctl --list-devices

# Update CAMERA_IDS in .env.pi to match your device
```

## Step 5: Test Camera Access

```bash
# Activate virtual environment
source venv/bin/activate

# Test camera detection
python3 -c "
from services.camera_manager import print_detected_cameras
print_detected_cameras()
"
```

## Step 6: Start the Service

```bash
# Manual start (for testing)
source venv/bin/activate
python pi_capture/main.py

# You should see:
# ✅ Camera manager ready
# ✅ Motion detector ready
# ✅ Capture started for camera 0
# 🌐 Access at: http://0.0.0.0:8090
```

## Step 7: Verify Operation

1. Open browser to `http://YOUR_PI_IP:8090`
2. You should see the Pi dashboard
3. Check camera status shows "active"
4. Wave your hand in front of camera to test motion detection

## Step 8: Set Up Auto-Start (Optional)

Create systemd service:
```bash
sudo nano /etc/systemd/system/birdcam.service
```

Add:
```ini
[Unit]
Description=BirdCam Capture Service
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/birdcam
Environment="PATH=/home/pi/birdcam/venv/bin"
ExecStart=/home/pi/birdcam/venv/bin/python pi_capture/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable service:
```bash
sudo systemctl enable birdcam
sudo systemctl start birdcam
sudo systemctl status birdcam
```

## Troubleshooting

### "No camera detected"
- Check camera connection
- Run `libcamera-hello --list-cameras`
- Ensure you're in the video group: `groups $USER`

### "Cannot connect to processing server"
- Verify PROCESSING_SERVER IP in .env.pi
- Check network: `ping YOUR_PROCESSING_SERVER_IP`
- Ensure processing server is running

### "Motion not triggering"
- Lower MOTION_THRESHOLD value
- Check motion box settings
- Verify camera 0 is the active camera

### Performance Issues
- Reduce FPS in .env.pi (try 5-10)
- Lower resolution (try 640x480)
- Ensure adequate cooling for Pi

## Multi-Camera Setup

For multiple cameras:

1. Set `CAMERA_IDS=0,1` in .env.pi
2. Camera 0 performs motion detection
3. All cameras record when motion detected
4. Each camera creates separate video files

## Next Steps

After Pi is running:
1. Set up the [AI Processing Server](PROCESSOR_SETUP.md)
2. Configure the [Web UI](../web-ui/README.md)
3. Create admin user on first login