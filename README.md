# BirdCam - Distributed Bird/Animal Detection System

A complete multi-camera bird and animal detection system with real-time monitoring, AI-powered detection, and web-based management interface.

## System Overview

The system consists of three main components:
- **Pi Capture** (Raspberry Pi): Motion-triggered video capture with multi-camera support using active/passive architecture
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
- Raspberry Pi 5 with Raspberry Pi OS (Pi 4+ also supported)
- Multiple CSI cameras or USB cameras connected
- Python 3.9+ (3.8+ supported but 3.9+ recommended)

**Processing Server:**
- Linux/Windows/macOS machine with Python 3.9+
- FFmpeg (required for video processing)
- GPU optional but recommended for faster processing

**System Dependencies:**
```bash
# Ubuntu/Debian (including Raspberry Pi OS):
sudo apt update && sudo apt install ffmpeg libopencv-dev python3-dev

# Raspberry Pi additional requirements:
sudo apt install python3-picamera2 libcamera-apps libcamera-dev

# Add user to video group for camera permissions:
sudo usermod -a -G video $USER

# macOS:
brew install ffmpeg

# Windows:
# Download FFmpeg from https://ffmpeg.org/
```

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
# Install system dependencies first (see Prerequisites section above)

# Install Python dependencies
pip install -r requirements.txt

# Setup camera permissions and configuration
./setup_pi_camera.sh

# IMPORTANT: Reboot if camera was just enabled
# sudo reboot

# Start the capture service
python pi_capture/main.py
```

**On Processing Server:**
```bash
# Install system dependencies first (see Prerequisites section above)

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

### 5. Network Configuration

**Important:** Ensure network connectivity between components:
- **Ports 8090 and 8091** must be accessible between Pi and Processing Server
- **Firewall rules** may need to be configured to allow these ports
- Both services need **bidirectional network access** for file sync and status updates

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

#### Database Storage
- **SQLite databases** are automatically created in camera-specific directories
- **Pi Capture:** `./bird_footage/camera_X/capture.db` 
- **AI Processor:** `./bird_footage/processing.db`
- No additional database setup required

## How It Works

### Multi-Camera System (Active/Passive Architecture)
- **Camera 0 (Active):** Performs motion detection and triggers recording
- **Camera 1+ (Passive):** Records when the active camera detects motion
- **Synchronized Recording:** All cameras capture the same events from different angles
- **Scalable:** Support for multiple cameras beyond just two

### Detection Pipeline
1. **Motion Detection:** Camera 0 monitors for movement
2. **Video Capture:** All cameras record 15s pre-motion + event + 30s post-motion
3. **File Sync:** Videos automatically sync to processing server every 15 minutes
4. **AI Processing:** YOLO analyzes videos for birds/animals
5. **Storage:** Detections kept 30 days, non-detections 7 days

### Web Interface Features
- **Live Feeds:** Real-time streams from all connected cameras
- **Detection Gallery:** Browse all detected animals with thumbnails
- **System Monitoring:** Status, storage usage, processing queue
- **Settings:** Configure motion detection, AI parameters, retention

## Development

### Running Tests
```bash
# Install test dependencies
pip install -r tests/requirements.txt

# Run comprehensive test suite
python run_tests.py

# Run specific test types
python run_tests.py --unit          # Unit tests only
python run_tests.py --integration   # Integration tests only
python run_tests.py --coverage      # With coverage report
python run_tests.py --html          # Generate HTML report

# Traditional pytest usage
pytest                    # Run all tests
pytest tests/unit/        # Unit tests only  
pytest tests/integration/ # Integration tests only
pytest --cov=.           # With coverage
```

### Startup Validation
The system includes comprehensive startup validation that checks:
- Python version and dependencies
- Database connectivity and table structure  
- Storage directory permissions
- Configuration validity
- System resources
- Network connectivity

Validation runs automatically when starting services and will prevent startup if critical issues are found.

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
- Check processing server is running: `python ai_processor/main.py`
- Verify videos are syncing: check `/bird_processing/incoming/`
- Review motion detection settings
- Check database path in logs - ensure it points to correct location

**"500 Internal Server Error"**
- Check startup validation logs for detailed error information
- Verify database tables exist: run `python run_tests.py --integration`
- Check storage path configuration in `.env`
- Review server logs for specific error details

**"Only Camera 0 detections showing"**
- This is fixed in the latest version with camera-specific filenames
- All cameras now create unique video files with camera IDs

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