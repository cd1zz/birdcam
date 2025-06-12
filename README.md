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
   echo "CAMERA_TYPE=picamera2" >> .env
   ```

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
   echo "CAMERA_TYPE=opencv" >> .env
   ```

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

### Multiple Cameras Detected
The system will automatically try each camera. Check logs for which camera is being used.

### Permission Errors
```bash
# Add user to video group
sudo usermod -a -G video $USER
# Log out and back in
```