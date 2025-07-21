# AI Processing Server Setup Guide

Complete guide for setting up the AI processing server that analyzes videos and hosts the web interface.

## System Requirements

### Minimum:
- 4GB RAM
- 2 CPU cores
- 50GB storage
- Python 3.9+

### Recommended:
- 8GB+ RAM
- 4+ CPU cores
- NVIDIA GPU (for faster processing)
- 100GB+ SSD storage
- Ubuntu 22.04 or similar

## Step 1: System Dependencies

### Ubuntu/Debian:
```bash
sudo apt update
sudo apt install -y \
    python3-pip \
    python3-venv \
    git \
    ffmpeg \
    libopencv-dev \
    python3-opencv
```

### macOS:
```bash
brew install python@3.10 ffmpeg opencv
```

### Windows:
1. Install Python 3.9+ from python.org
2. Install FFmpeg from ffmpeg.org
3. Add both to PATH

## Step 2: Clone and Configure

```bash
# Clone repository
git clone https://github.com/yourusername/birdcam.git
cd birdcam

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install processor dependencies
pip install -r requirements.processor.txt

# Create configuration
cp config/examples/.env.processor.example .env.processor
nano .env.processor
```

## Step 3: Basic Configuration

Edit `.env.processor`:

```bash
# Storage location for videos
STORAGE_PATH=./bird_processing

# AI Model (smaller = faster, larger = more accurate)
MODEL_NAME=yolov5n    # Options: yolov5n, yolov5s, yolov5m, yolov5l

# What to detect
DETECTION_CLASSES=bird,cat,dog,person

# Web interface port
PROCESSING_PORT=8091
```

## Step 4: GPU Setup (Optional but Recommended)

### NVIDIA GPU:
```bash
# Check if CUDA is available
python3 -c "import torch; print(torch.cuda.is_available())"

# If False, install CUDA toolkit:
# Ubuntu: sudo apt install nvidia-cuda-toolkit
# Or visit: https://developer.nvidia.com/cuda-downloads
```

### Apple Silicon:
```bash
# MPS acceleration is automatic if available
python3 -c "import torch; print(torch.backends.mps.is_available())"
```

## Step 5: Test the Setup

```bash
# Activate environment
source venv/bin/activate

# Test AI model loading
python3 -c "
from services.ai_model_manager import ModelManager
from config.settings import Config
config = Config()
model = ModelManager(config.detection)
print('✅ Model loaded successfully')
"
```

## Step 6: Start the Processing Server

```bash
# Manual start
source venv/bin/activate
python ai_processor/main.py

# You should see:
# ✅ Model yolov5n loaded successfully
# 🌐 Processing Dashboard ready!
# 🌐 Access at: http://0.0.0.0:8091
```

## Step 7: Set Up Web UI

The modern React interface needs to be built:

```bash
# Navigate to web UI directory
cd web-ui

# Install dependencies
npm install

# Configure API endpoints
cp ../config/examples/.env.web-ui.example .env
nano .env
```

Edit `web-ui/.env`:
```bash
VITE_PI_SERVER=http://192.168.1.50:8090         # Your Pi's address
VITE_PROCESSING_SERVER=http://192.168.1.100:8091 # This server's address
```

Build and serve:
```bash
# Production build
npm run build

# The built files are automatically served by the processor at port 8091
```

## Step 8: Initial Admin Setup

1. Open browser to `http://YOUR_SERVER_IP:8091`
2. You'll be redirected to `/setup`
3. Create admin account (must be on local network)
4. Log in with your new credentials

## Step 9: Verify Everything Works

1. **Check Pi Connection**: 
   - Go to Settings → System
   - Pi status should show "Connected"

2. **Process Test Video**:
   - Place a test .mp4 in `bird_processing/incoming/`
   - Check dashboard - should show processing

3. **View Live Feeds**:
   - Go to Live Feeds tab
   - Should see camera streams from Pi

## Step 10: Auto-Start Service (Optional)

### Systemd (Linux):
```bash
sudo nano /etc/systemd/system/birdcam-processor.service
```

Add:
```ini
[Unit]
Description=BirdCam AI Processor
After=network.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/home/YOUR_USER/birdcam
Environment="PATH=/home/YOUR_USER/birdcam/venv/bin"
ExecStart=/home/YOUR_USER/birdcam/venv/bin/python ai_processor/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl enable birdcam-processor
sudo systemctl start birdcam-processor
```

## Performance Tuning

### For Faster Processing:
```bash
# In .env.processor:
PROCESS_EVERY_NTH_FRAME=5    # Skip more frames
MODEL_NAME=yolov5n           # Use smaller model
MAX_THUMBNAILS_PER_VIDEO=3   # Generate fewer thumbnails
```

### For Better Accuracy:
```bash
# In .env.processor:
PROCESS_EVERY_NTH_FRAME=1    # Process every frame
MODEL_NAME=yolov5l           # Use larger model
BIRD_CONFIDENCE=0.25         # Lower threshold
```

## Storage Management

The system automatically manages storage:
- Videos WITH detections: kept 30 days
- Videos WITHOUT detections: kept 7 days
- Adjust in .env.processor:
  ```bash
  DETECTION_RETENTION_DAYS=30
  NO_DETECTION_RETENTION_DAYS=7
  ```

## Troubleshooting

### "Model failed to load"
- Check internet connection (first run downloads model)
- Verify PyTorch installation: `pip show torch`
- Try smaller model: `MODEL_NAME=yolov5n`

### "Cannot connect to Pi"
- Verify Pi is running: `curl http://PI_IP:8090/api/status`
- Check firewall allows port 8090
- Verify both systems on same network

### "Processing very slow"
- Check CPU/GPU usage: `htop` or `nvidia-smi`
- Increase PROCESS_EVERY_NTH_FRAME
- Consider GPU upgrade

### "Web UI not loading"
- Check processor is running: `curl http://localhost:8091/api/health`
- Verify web UI built: `ls web-ui/dist/`
- Check browser console for errors

## Next Steps

1. Configure detection classes for your needs
2. Adjust confidence thresholds
3. Set up additional users
4. Configure motion zones in web UI
5. Monitor storage usage