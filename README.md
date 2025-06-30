# 📷 Camera Setup Guide

## Pi Camera (Pi AI Camera, Pi Camera Module, etc.)

### Quick Setup (Recommended)
```bash
# Run the automated setup script
chmod +x setup_pi_camera.sh
./setup_pi_camera.sh
```

### Manual Setup
1. **Enable Camera Interface**
   ```bash
   sudo raspi-config
   # Go to: Interface Options → Camera → Enable
   # Reboot when prompted
   ```

2. **Install System Dependencies**
   ```bash
   sudo apt update
   sudo apt install -y python3-picamera2 libcamera-apps libcamera-dev
   ```

3. **Create Virtual Environment with System Access**
   ```bash
   # IMPORTANT: Use --system-site-packages for camera access
   python3 -m venv .venv --system-site-packages
   source .venv/bin/activate
   ```

4. **Install Requirements**
   ```bash
   # Remove picamera2 from requirements.txt if present (use system version)
   pip install -r requirements.txt
   ```

5. **Configure Environment**
   ```bash
   cp .env.example .env
   ```
   Adjust other settings in `.env` as needed.

6. **Test Camera**
   ```bash
   python3 -c "from picamera2 import Picamera2; print('Cameras:', Picamera2.global_camera_info())"
   ```

## USB Camera

### Setup
1. **Create Standard Virtual Environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Install Requirements**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` to suit your setup.

## Troubleshooting

### "Camera Not Available" Error
- **Pi Camera**: Make sure you used `--system-site-packages` when creating venv
- **USB Camera**: Check camera is connected and accessible with `ls /dev/video*`

### "No module named 'libcamera'" Error
```bash
# Install system camera packages
sudo apt install -y python3-picamera2 libcamera-apps

# Recreate venv with system access
rm -rf .venv
python3 -m venv .venv --system-site-packages
source .venv/bin/activate
pip install -r requirements.txt
```

### Multiple Cameras
Birdcam can run several cameras at once. List camera IDs in `CAMERA_IDS`.

Example:

```bash
CAMERA_IDS=0,1
```

### Permission Errors
```bash
# Add user to video group
sudo usermod -a -G video $USER
# Log out and back in
```

### Blue or Distorted Colors
When using the Picamera2 library, the camera may deliver frames in
RGB order. Birdcam now converts these frames to BGR before processing,
so colors in the live feed should look normal. If you still see a blue
hue, ensure you have updated to the latest version.

### Event Grouping
The processing server now groups detections that occur close in time and
space into a single event. The `/api/recent-detections` endpoint returns
these events with a `count` field indicating how many detections were
clustered together. This keeps the dashboard from filling up with many
frames from the same visitor.
