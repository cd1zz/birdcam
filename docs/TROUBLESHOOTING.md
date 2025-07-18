# Troubleshooting Guide

Common issues and solutions for BirdCam setup and operation.

## Quick Diagnostics

### Check System Status
```bash
# On Pi - Check if capture is running
curl http://localhost:8090/api/status

# On Processor - Check if AI service is running  
curl http://localhost:8091/api/health

# Test Pi → Processor connection
# From Pi:
curl http://YOUR_PROCESSOR_IP:8091/api/health
```

## Raspberry Pi Issues

### "No camera detected"

**CSI Camera:**
```bash
# Check if camera is enabled
sudo raspi-config
# Navigate to: Interface Options → Camera → Enable

# List cameras
libcamera-hello --list-cameras

# If no cameras shown:
# 1. Check ribbon cable connection
# 2. Try flipping cable at camera end
# 3. Reboot: sudo reboot
```

**USB Camera:**
```bash
# List video devices
ls /dev/video*

# Check camera details
v4l2-ctl --list-devices

# Update CAMERA_IDS in .env.pi to match device number
```

### "Motion not triggering"

1. **Check motion settings:**
   ```bash
   # Edit .env.pi
   MOTION_THRESHOLD=3000      # Try lowering (was 5000)
   MIN_CONTOUR_AREA=300      # Try lowering (was 500)
   ```

2. **Verify motion box:**
   - Open web UI → Settings → Motion
   - Ensure motion box covers area of interest
   - Check "Motion Box Enabled" is ON

3. **Test with debug info:**
   ```python
   # In Python console:
   from services.motion_detector import MotionDetector
   # Check motion detector status
   ```

### "Cannot connect to processing server"

1. **Check network:**
   ```bash
   # From Pi:
   ping YOUR_PROCESSOR_IP
   
   # Check if port is open:
   nc -zv YOUR_PROCESSOR_IP 8091
   ```

2. **Verify configuration:**
   ```bash
   grep PROCESSING_SERVER .env.pi
   # Should show correct IP
   ```

3. **Check firewall:**
   ```bash
   # On processor:
   sudo ufw status
   # If enabled, allow port:
   sudo ufw allow 8091
   ```

## Processing Server Issues

### "Model failed to load"

1. **First run downloads model:**
   ```bash
   # Check internet connection
   ping google.com
   
   # Manually download model:
   python -c "import torch; torch.hub.load('ultralytics/yolov5', 'yolov5n')"
   ```

2. **Check PyTorch installation:**
   ```bash
   python -c "import torch; print(torch.__version__)"
   ```

3. **Try smaller model:**
   ```bash
   # In .env.processor:
   MODEL_NAME=yolov5n  # Instead of yolov5s/m/l
   ```

### "Processing very slow"

1. **Check GPU availability:**
   ```bash
   # NVIDIA:
   nvidia-smi
   python -c "import torch; print(torch.cuda.is_available())"
   
   # Apple Silicon:
   python -c "import torch; print(torch.backends.mps.is_available())"
   ```

2. **Optimize settings:**
   ```bash
   # In .env.processor:
   PROCESS_EVERY_NTH_FRAME=5   # Skip more frames
   MODEL_NAME=yolov5n          # Use faster model
   ```

3. **Monitor resources:**
   ```bash
   htop  # Check CPU/RAM usage
   ```

### "No detections appearing"

1. **Check video files arriving:**
   ```bash
   ls -la bird_processing/incoming/
   # Should see .mp4 files from Pi
   ```

2. **Check processing logs:**
   ```bash
   # Look for processing messages
   grep "Processing:" ai_processor.log
   ```

3. **Verify detection settings:**
   ```bash
   # Lower confidence thresholds in .env.processor:
   BIRD_CONFIDENCE=0.25   # Was 0.35
   DEFAULT_CONFIDENCE=0.25
   ```

## Web UI Issues

### "Cannot access web interface"

1. **Check service is running:**
   ```bash
   curl http://localhost:8091
   # Should return HTML
   ```

2. **Check if built:**
   ```bash
   ls web-ui/dist/
   # Should see index.html and assets
   
   # If missing, build:
   cd web-ui
   npm install
   npm run build
   ```

3. **Browser issues:**
   - Clear cache (Ctrl+Shift+R)
   - Check browser console (F12)
   - Try different browser

### "Mixed content errors (HTTPS)"

When accessing through HTTPS proxy:

1. **Update web-ui/.env:**
   ```bash
   VITE_PI_SERVER=https://pi.yourdomain.com
   VITE_PROCESSING_SERVER=https://processor.yourdomain.com
   ```

2. **Rebuild UI:**
   ```bash
   cd web-ui
   npm run build
   ```

### "Login issues"

1. **First time setup:**
   - Must be on local network for initial admin creation
   - Check browser shows local IP, not external

2. **Forgot password:**
   ```bash
   # Create new admin:
   python setup_admin.py
   ```

3. **Token errors:**
   - Clear browser localStorage
   - Try incognito/private mode

## Database Issues

### "Database locked"

```bash
# Find and stop duplicate processes:
ps aux | grep python
# Kill duplicate: kill PID

# If persists, restart services
```

### "Table not found"

```bash
# Recreate tables:
python -c "
from database.connection import DatabaseManager
from database.repositories.video_repository import VideoRepository
db = DatabaseManager('path/to/db')
repo = VideoRepository(db)
repo.create_table()
"
```

## Performance Optimization

### Reduce CPU Usage
```bash
# .env.pi:
FPS=5                       # Lower framerate
RESOLUTION_WIDTH=640        # Lower resolution
RESOLUTION_HEIGHT=480

# .env.processor:
PROCESS_EVERY_NTH_FRAME=10  # Process fewer frames
```

### Reduce Storage Usage
```bash
# .env.processor:
NO_DETECTION_RETENTION_DAYS=3  # Keep less
MAX_THUMBNAILS_PER_VIDEO=2     # Fewer thumbnails
```

### Reduce Network Usage
```bash
# .env.pi:
SYNC_INTERVAL_MINUTES=60    # Sync less often
RESOLUTION_WIDTH=320        # Smaller videos
```

## Debug Commands

### Check Service Logs
```bash
# Recent system logs
journalctl -u birdcam -n 50

# Python errors
python pi_capture/main.py 2>&1 | tee debug.log
```

### Test Components
```bash
# Test camera
python -c "from services.camera_manager import CameraManager; cm = CameraManager(...); print(cm.list_cameras())"

# Test AI model
python -c "from services.ai_model_manager import ModelManager; mm = ModelManager(...); print('OK')"

# Test database
python -c "from database.connection import DatabaseManager; db = DatabaseManager('test.db'); print('OK')"
```

## Getting Help

When reporting issues, include:

1. **System info:**
   ```bash
   python --version
   uname -a
   ```

2. **Configuration:**
   ```bash
   grep -v SECRET .env.pi
   grep -v SECRET .env.processor
   ```

3. **Error messages:**
   - Full error traceback
   - Recent log entries

4. **What you tried:**
   - Steps to reproduce
   - Solutions attempted