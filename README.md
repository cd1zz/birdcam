# BirdCam - Distributed Bird/Animal Detection System

A complete dual-camera bird and animal detection system with real-time monitoring, AI-powered detection, and web-based management interface.

## System Overview

The system consists of three main components:
- **Pi Capture** (Raspberry Pi): Motion-triggered video capture with dual camera support
- **AI Processor** (Server): YOLO-based object detection on video segments  
- **Web UI** (React/TypeScript): Live monitoring, detection viewing, and system management

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Raspberry Pi  │    │  Processing     │    │   Web Browser   │
│                 │    │     Server      │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │   Camera 0  │ │    │ │YOLO Detection│ │    │ │   Web UI    │ │
│ │  (Active)   │ │    │ │   Service   │ │    │ │ (React App) │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │                 │
│ │   Camera 1  │ │────│ │File Storage │ │────│                 │
│ │  (Passive)  │ │    │ │& Database   │ │    │                 │
│ └─────────────┘ │    │ └─────────────┘ │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Quick Start

### 1. Prerequisites

**Raspberry Pi:**
- Raspberry Pi 4+ with Raspberry Pi OS
- Two CSI cameras or USB cameras connected
- Python 3.8+

**Processing Server:**
- Linux/Windows/macOS machine with Python 3.8+
- GPU optional but recommended for faster processing

### 2. Configuration Setup

**IMPORTANT:** You need to configure two separate `.env` files:

#### Backend Configuration (Root Directory)
```bash
# Copy and edit the main configuration
cp .env.example .env
nano .env
```

Key settings to configure:
```bash
# Update with your network IPs
PROCESSING_SERVER=192.168.1.100  # IP of your processing server
CAPTURE_PORT=8090                # Pi web interface port

# Camera setup
CAMERA_IDS=0,1                   # Enable both cameras
RESOLUTION_WIDTH=640
RESOLUTION_HEIGHT=480

# Motion detection sensitivity
MOTION_THRESHOLD=5000            # Lower = more sensitive
MIN_CONTOUR_AREA=500            # Minimum size to trigger

# Detection classes
DETECTION_CLASSES=bird,cat,dog,person
BIRD_CONFIDENCE=0.35
```

#### Frontend Configuration (Web UI)
```bash
# Configure the web interface
cd web-ui
cp .env.example .env
nano .env
```

Update with your actual IP addresses:
```bash
# URL to Pi capture system (from browser perspective)
VITE_PI_SERVER=http://192.168.1.50:8090

# URL to processing server (from browser perspective)  
VITE_PROCESSING_SERVER=http://192.168.1.100:8091
```

### 3. Installation

**On Raspberry Pi:**
```bash
# Install Python dependencies
pip install -r requirements.txt

# Setup camera permissions
./setup_pi_camera.sh

# Start the capture service
python pi_capture/main.py
```

**On Processing Server:**
```bash
# Install Python dependencies
pip install -r requirements.txt

# Start the AI processor
python ai_processor/main.py
```

**Web UI (on either machine):**
```bash
cd web-ui
npm install
npm run build
npm run preview  # Or 'npm run dev' for development
```

### 4. Access the System

- **Pi Dashboard:** http://YOUR_PI_IP:8090
- **Processing Dashboard:** http://YOUR_PROCESSING_SERVER:8091  
- **Web UI:** Served from either dashboard

## Configuration Details

### Environment Files Explained

| File | Purpose | Used By |
|------|---------|---------|
| `/.env` | Backend services configuration | Pi Capture & AI Processor |
| `/web-ui/.env` | Frontend API endpoints | React Web UI |

### Key Configuration Options

#### Camera Setup
```bash
CAMERA_IDS=0,1                   # Comma-separated camera IDs
FPS=10                          # Frames per second
RESOLUTION_WIDTH=640            # Video resolution
RESOLUTION_HEIGHT=480
```

#### Motion Detection
```bash
MOTION_THRESHOLD=5000           # Sensitivity (lower = more sensitive)
MIN_CONTOUR_AREA=500           # Minimum motion size to trigger
MOTION_TIMEOUT_SECONDS=30      # Recording duration after motion stops
```

#### AI Detection
```bash
DETECTION_CLASSES=bird,cat,dog  # What to detect
BIRD_CONFIDENCE=0.35           # Detection confidence thresholds
MODEL_NAME=yolov5n             # AI model to use
```

#### Network Configuration
```bash
# Backend (.env)
PROCESSING_SERVER=192.168.1.100  # Processing server IP
PROCESSING_PORT=8091

# Frontend (web-ui/.env)
VITE_PI_SERVER=http://192.168.1.50:8090        # Pi URL
VITE_PROCESSING_SERVER=http://192.168.1.100:8091  # Processing URL
```

## How It Works

### Dual Camera System
- **Camera 0 (Active):** Performs motion detection
- **Camera 1 (Passive):** Records when Camera 0 detects motion
- **Synchronized Recording:** Both cameras capture the same events from different angles

### Detection Pipeline
1. **Motion Detection:** Camera 0 monitors for movement
2. **Video Capture:** Both cameras record 15s pre-motion + event + 30s post-motion
3. **File Sync:** Videos automatically sync to processing server every 15 minutes
4. **AI Processing:** YOLO analyzes videos for birds/animals
5. **Storage:** Detections kept 30 days, non-detections 7 days

### Web Interface Features
- **Live Feeds:** Real-time streams from both cameras
- **Detection Gallery:** Browse all detected animals with thumbnails
- **System Monitoring:** Status, storage usage, processing queue
- **Settings:** Configure motion detection, AI parameters, retention

## Development

### Running Tests
```bash
# Run all tests
pytest

# Run specific test categories  
pytest tests/unit/
pytest tests/integration/

# Run with coverage
pytest --cov=.
```

### Development Commands
```bash
# Backend services
python pi_capture/main.py     # Pi capture system
python ai_processor/main.py   # AI processing server

# Frontend development
cd web-ui
npm run dev                   # Start dev server
npm run lint                  # Check code style
npm run build                 # Production build
```

## Troubleshooting

### Common Issues

**"Cannot connect to Pi camera system"**
- Check Pi is running: `python pi_capture/main.py`
- Verify IP address in `web-ui/.env`
- Ensure port 8090 is open

**"No camera detected"**
- Run: `libcamera-hello --list-cameras`
- Check camera connections
- Verify permissions: `./setup_pi_camera.sh`

**"No detections appearing"**
- Check processing server is running
- Verify videos are syncing: check `/bird_footage/incoming/`
- Review motion detection settings

**"Only Camera 0 detections showing"**
- This is fixed in the latest version with camera-specific filenames
- Both cameras now create unique video files

### Log Files
- Pi Capture: Check console output
- AI Processor: `ai_processor.log`
- Web UI: Browser developer console

## File Structure

```
├── pi_capture/           # Raspberry Pi capture system
├── ai_processor/         # AI processing service  
├── web-ui/              # React frontend application
├── services/            # Core business logic
├── database/            # Data access layer
├── config/              # Configuration management
├── web/                 # Flask API routes
├── tests/               # Test suite
├── .env.example         # Backend configuration template
└── README.md           # This file
```

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions:
- Check the troubleshooting section above
- Review logs for error messages
- Create an issue on GitHub with:
  - System configuration 
  - Steps to reproduce
  - Error messages/logs