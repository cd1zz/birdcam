# Environment Files Configuration Guide

This guide explains the role of each `.env` file in the BirdCam system and how to configure them properly.

## Overview of Environment Files

The BirdCam system uses multiple `.env` files for different components:

```
birdcam/
├── config/
│   └── examples/
│       ├── .env.pi.example          # Template for Raspberry Pi configuration
│       ├── .env.processor.example   # Template for AI Processor configuration
│       └── .env.example            # Legacy unified template (deprecated)
    │       ├── .env.web-ui.example      # Standard Web UI configuration (direct access)
    │       └── .env.proxy.example       # Secure proxy configuration (single tunnel)
    └── web-ui/
```

## 1. Raspberry Pi Configuration (`.env.pi`)

**Location**: On the Raspberry Pi at `/home/pi/birdcam/.env.pi`  
**Purpose**: Configure camera capture, motion detection, and sync settings

### Key Settings:

```bash
# Camera Configuration
CAMERA_IDS=0,1              # Comma-separated camera IDs
FPS=10                      # Frames per second
RESOLUTION_WIDTH=640        # Video width
RESOLUTION_HEIGHT=480       # Video height

# Motion Detection
MOTION_THRESHOLD=5000       # Sensitivity (lower = more sensitive)
MIN_CONTOUR_AREA=500       # Minimum object size
MOTION_BOX_ENABLED=true    # Enable detection zones

# Processing Server Connection
PROCESSING_SERVER=192.168.1.200  # IP of your AI server
PROCESSING_PORT=8091            # AI server port

# Local Web Interface
CAPTURE_PORT=8090          # Pi's web interface port
HOST=0.0.0.0              # Listen on all interfaces
```

### Usage:
```bash
cp config/examples/.env.pi.example .env.pi
nano .env.pi  # Edit with your settings
```

## 2. AI Processor Configuration (`.env.processor`)

**Location**: On the AI server at `/path/to/birdcam/.env.processor`  
**Purpose**: Configure AI detection, storage, authentication, and proxy settings

### Key Settings:

```bash
# Storage
STORAGE_PATH=./bird_processing     # Where videos are stored

# AI Detection
DETECTION_CLASSES=bird,cat,dog,person
MODEL_NAME=yolov5n                # YOLO model size
BIRD_CONFIDENCE=0.35              # Detection thresholds

# Retention
DETECTION_RETENTION_DAYS=30       # Keep detections for 30 days
NO_DETECTION_RETENTION_DAYS=7     # Keep non-detections for 7 days

# Web Interface
PROCESSING_PORT=8091              # Web UI port
SECRET_KEY=your-secret-key        # JWT authentication key

# NEW: Pi Proxy Settings (for secure single-tunnel setup)
CAPTURE_SERVER=192.168.1.100      # Internal IP of your Pi
CAPTURE_PORT=8090                 # Pi's port
```

### Important Security Note:
Always generate a secure `SECRET_KEY`:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Usage:
```bash
cp config/examples/.env.processor.example .env.processor
nano .env.processor  # Edit with your settings
```

## 3. Web UI Configuration

The Web UI can be configured in two modes:

### Option A: Direct Access Mode (`.env`)

**When to use**: Local network only, or when you have two CloudFlare tunnels

```bash
# Direct access to both servers
VITE_PROCESSING_SERVER=http://192.168.1.200:8091
VITE_PI_SERVER=http://192.168.1.100:8090
```

### Option B: Secure Proxy Mode (`.env.proxy.example`)

**When to use**: Internet access with single CloudFlare tunnel (recommended)

```bash
# Proxy mode - all requests go through AI Processor
VITE_PROCESSING_SERVER=https://birdcam.yourdomain.com
VITE_PI_SERVER=                  # Leave empty for proxy mode!
```

### Usage:
```bash
cd web-ui

# For direct access:
cp ../config/examples/.env.web-ui.example .env

# For secure proxy:
cp ../config/examples/.env.proxy.example .env

nano .env  # Edit with your settings
npm run build
```

## Configuration Scenarios

### Scenario 1: Local Network Only

**Pi** (`.env.pi`):
```bash
PROCESSING_SERVER=192.168.1.200
PROCESSING_PORT=8091
```

**Processor** (`.env.processor`):
```bash
CAPTURE_SERVER=192.168.1.100
CAPTURE_PORT=8090
```

**Web UI** (`.env`):
```bash
VITE_PROCESSING_SERVER=http://192.168.1.200:8091
VITE_PI_SERVER=http://192.168.1.100:8090
```

### Scenario 2: Internet Access (Secure Proxy)

**Pi** (`.env.pi`):
```bash
PROCESSING_SERVER=192.168.1.200  # Still uses internal IP
PROCESSING_PORT=8091
```

**Processor** (`.env.processor`):
```bash
CAPTURE_SERVER=192.168.1.100     # Internal Pi IP
CAPTURE_PORT=8090
SECRET_KEY=<secure-generated-key>
```

**Web UI** (`.env`):
```bash
VITE_PROCESSING_SERVER=https://birdcam.yourdomain.com
VITE_PI_SERVER=                  # Empty enables proxy mode
```

## Migration from Old Setup

If you're upgrading from an older version:

1. **Split the old `.env` file**:
   - Copy camera/motion settings to `.env.pi`
   - Copy AI/storage settings to `.env.processor`

2. **Add new proxy settings** to `.env.processor`:
   ```bash
   CAPTURE_SERVER=<your-pi-ip>
   CAPTURE_PORT=8090
   ```

3. **Update Web UI** for proxy mode if using internet access

## Troubleshooting

### Web UI can't connect to cameras
- **Direct mode**: Ensure both `VITE_PROCESSING_SERVER` and `VITE_PI_SERVER` are set
- **Proxy mode**: Ensure `VITE_PI_SERVER` is empty and `CAPTURE_SERVER` is set in processor

### Authentication errors (401)
- Verify `SECRET_KEY` is set in `.env.processor`
- Check token exists: `localStorage.getItem('accessToken')` in browser console
- Try logging out and back in

### "Failed to connect to Pi"
- Check `CAPTURE_SERVER` and `CAPTURE_PORT` in `.env.processor`
- Test connection: `curl http://192.168.1.100:8090/api/status`

### Videos not syncing
- Verify `PROCESSING_SERVER` in `.env.pi` points to correct IP
- Check both services are running
- Look for sync errors in Pi logs

## Security Best Practices

1. **Always use proxy mode** for internet access
2. **Generate secure keys**: Never use default SECRET_KEY
3. **Use HTTPS**: CloudFlare tunnels provide this automatically
4. **Internal IPs only**: Keep Pi on internal network
5. **Regular updates**: Keep both systems updated

## Environment Variable Reference

See individual `.env.*.example` files for complete list of available settings and their descriptions.