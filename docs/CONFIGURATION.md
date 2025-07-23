# Configuration Reference

Complete reference for all configuration options in BirdCam.

## Configuration Files Overview

| File | Location | Purpose |
|------|----------|---------|
| `.env.pi` | Raspberry Pi | Camera and motion settings |
| `.env.processor` | AI Server | Detection and storage settings |
| `web-ui/.env` | AI Server | Frontend API endpoints |

## Raspberry Pi Configuration (.env.pi)

### Network Settings
```bash
PROCESSING_SERVER=192.168.1.100  # IP of AI processing server (REQUIRED)
PROCESSING_PORT=8091             # Port of processing server API
```

### Camera Configuration
```bash
CAMERA_IDS=0                     # Single camera: 0, Multiple: 0,1,2
FPS=10                          # Frames per second (5-30)
RESOLUTION_WIDTH=640            # Video width in pixels
RESOLUTION_HEIGHT=480           # Video height in pixels
```

### Motion Detection
```bash
# Sensitivity Settings
MOTION_THRESHOLD=5000           # 1000-10000 (lower = more sensitive)
MIN_CONTOUR_AREA=500           # Minimum pixels to trigger (100-2000)
LEARNING_RATE=0.01             # Background adaptation rate (0.001-0.1)

# Timing Settings  
MOTION_TIMEOUT_SECONDS=30      # Continue recording N seconds after motion
MAX_SEGMENT_DURATION=300       # Maximum video length in seconds
PRE_MOTION_BUFFER_SECONDS=15   # Seconds to save before motion

# Detection Zone
MOTION_BOX_ENABLED=true        # Enable detection zone
MOTION_BOX_X1=0               # Top-left X coordinate
MOTION_BOX_Y1=0               # Top-left Y coordinate
MOTION_BOX_X2=640             # Bottom-right X coordinate
MOTION_BOX_Y2=480             # Bottom-right Y coordinate
```

### Storage and Sync
```bash
STORAGE_PATH=./bird_footage     # Local video storage location
SYNC_INTERVAL_MINUTES=15       # How often to sync to server
UPLOAD_TIMEOUT_SECONDS=300     # Maximum upload time
PI_CLEANUP_DAYS=3             # Delete local files after N days
```

### Web Interface
```bash
CAPTURE_PORT=8090              # Pi web API port
HOST=0.0.0.0                  # Listen address (0.0.0.0 = all)
CORS_ENABLED=true             # Allow cross-origin requests
```

## AI Processor Configuration (.env.processor)

### Storage
```bash
STORAGE_PATH=./bird_processing  # Where to store all videos/data
```

### AI Detection Settings
```bash
# Model Selection
MODEL_NAME=yolov8n             # Options: yolov8n/s/m/l/x
                              # n=nano (fastest), x=extra large (most accurate)

# Processing Options
PROCESS_EVERY_NTH_FRAME=3      # Skip frames (1-10, higher=faster)
MAX_THUMBNAILS_PER_VIDEO=5     # Thumbnail generation limit

# Detection Classes
DETECTION_CLASSES=bird,cat,dog,person,horse,sheep,cow,elephant,bear,zebra,giraffe
```

### Confidence Thresholds
```bash
# Per-class confidence (0.0-1.0)
BIRD_CONFIDENCE=0.35           # Bird detection threshold
CAT_CONFIDENCE=0.40            # Cat detection threshold
DOG_CONFIDENCE=0.30            # Dog detection threshold
PERSON_CONFIDENCE=0.50         # Person detection threshold
DEFAULT_CONFIDENCE=0.35        # For unlisted classes
```

### Retention Policies
```bash
DETECTION_RETENTION_DAYS=30    # Keep videos WITH detections
NO_DETECTION_RETENTION_DAYS=7  # Keep videos WITHOUT detections
```

### Web Interface
```bash
PROCESSING_PORT=8091           # Web UI port
HOST=0.0.0.0                  # Listen address
CORS_ENABLED=true             # Allow cross-origin requests
MAX_CONTENT_LENGTH=524288000  # Max upload size (bytes)
```

### Authentication
```bash
SECRET_KEY=your-secret-key     # JWT signing key (CHANGE THIS!)
# Generate: python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Web UI Configuration (web-ui/.env)

```bash
# API Endpoints (from browser's perspective)
VITE_PI_SERVER=http://192.168.1.50:8090         # Pi camera system
VITE_PROCESSING_SERVER=http://192.168.1.100:8091 # AI processor
```

## Configuration Tips

### For Better Detection
- Decrease confidence thresholds (e.g., 0.25 instead of 0.35)
- Use larger model (yolov8m or yolov8l)
- Process more frames (PROCESS_EVERY_NTH_FRAME=1)

### For Faster Processing
- Increase confidence thresholds
- Use smaller model (yolov8n)
- Skip more frames (PROCESS_EVERY_NTH_FRAME=5)

### For Reduced False Positives
- Increase MOTION_THRESHOLD (e.g., 8000)
- Increase MIN_CONTOUR_AREA (e.g., 1000)
- Define smaller MOTION_BOX area

### For Network Issues
- Increase UPLOAD_TIMEOUT_SECONDS
- Decrease video resolution
- Lower FPS setting

## Environment Variable Precedence

1. System environment variables (highest priority)
2. .env.pi or .env.processor file
3. .env file (fallback)
4. Default values in code (lowest priority)

## Validating Configuration

Check your configuration:
```bash
# On Pi
python -c "from config.settings import Config; c=Config(); print(c.capture)"

# On Processor
python -c "from config.settings import Config; c=Config(); print(c.detection)"
```

## Common Issues

### "PROCESSING_SERVER not set"
- Most critical setting on Pi
- Must be IP address accessible from Pi
- Test with: `ping YOUR_PROCESSING_SERVER_IP`

### Videos not syncing
- Check SYNC_INTERVAL_MINUTES (default 15)
- Verify PROCESSING_PORT matches on both systems
- Check firewall rules

### Wrong detection results
- Adjust class-specific confidence values
- Try different MODEL_NAME
- Check DETECTION_CLASSES includes what you want

## Logging Configuration

### Access Logging
The AI Processing Server automatically logs all HTTP requests to syslog/journald with the identifier `birdcam.access`. 

**View access logs:**
```bash
# Real-time logs
sudo journalctl -t birdcam.access -f

# Last 100 entries
sudo journalctl -t birdcam.access -n 100

# Or check syslog directly
grep birdcam.access /var/log/syslog
```

**Log format:** Combined Log Format (Apache/Nginx style)
```
remote_addr - remote_user [timestamp] "request_line" status_code response_size "referer" "user_agent" duration
```

**Note:** Currently only the AI Processing Server has access logging enabled. The Pi Capture service does not log HTTP requests.