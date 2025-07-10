# BirdCam Project Context for AI Assistants

## Project Overview
BirdCam is a comprehensive AI-powered wildlife detection system built in Python. It's designed as a distributed system with two main components:

1. **Pi Capture System** - Runs on Raspberry Pi for motion detection and video recording
2. **AI Processing Server** - Runs on a server for AI analysis and detection clustering

## System Architecture

### Core Components

#### Pi Capture System (`pi_capture/main.py`)
- **Purpose**: Motion detection and video recording on Raspberry Pi
- **Key Services**:
  - Motion detection with configurable regions
  - Multi-camera support (Pi Camera, USB cameras)
  - Video segmentation and recording
  - File synchronization to processing server
  - Web dashboard for monitoring and configuration

#### AI Processing Server (`ai_processor/main.py`)
- **Purpose**: AI analysis and detection clustering
- **Key Services**:
  - YOLOv5-based bird/animal detection
  - Detection clustering by time and location
  - Thumbnail generation
  - Scheduled processing and cleanup
  - Web API for results

### Key Technologies
- **Flask**: Web framework for dashboards and APIs
- **OpenCV**: Computer vision and video processing
- **PyTorch/YOLOv5**: AI model for object detection
- **SQLite**: Database for storing videos and detections
- **Picamera2**: Raspberry Pi camera interface
- **Schedule**: Task scheduling

## Directory Structure

```
birdcam/
├── ai_processor/          # AI processing server
│   └── main.py           # Server entry point
├── pi_capture/           # Pi capture system
│   └── main.py           # Capture entry point
├── config/               # Configuration management
│   └── settings.py       # Environment-based config
├── core/                 # Data models
│   └── models.py         # Data classes
├── database/             # Database layer
│   ├── connection.py     # Database manager
│   └── repositories/     # Data access layer
├── services/             # Business logic
│   ├── ai_model_manager.py
│   ├── camera_manager.py
│   ├── capture_service.py
│   ├── motion_detector.py
│   ├── processing_service.py
│   └── video_writer.py
├── web/                  # Web interface
│   ├── app.py           # Flask app factory
│   ├── routes/          # API endpoints
│   ├── static/          # CSS/JS assets
│   └── templates/       # HTML templates
└── requirements.txt      # Python dependencies
```

## Configuration System

### Environment Variables
The system uses environment variables for configuration loaded via `python-dotenv`:

**Key Variables:**
- `CAMERA_IDS`: Comma-separated camera IDs (auto-detects if not set)
- `STORAGE_PATH`: Base storage directory
- `PROCESSING_SERVER`: IP address of processing server
- `DETECTION_CLASSES`: Comma-separated detection classes (bird, cat, dog, etc.)
- `MODEL_NAME`: YOLOv5 model variant (yolov5n, yolov5s, etc.)
- `MOTION_THRESHOLD`: Motion detection sensitivity
- `DETECTION_RETENTION_DAYS`: Days to keep videos with detections
- `NO_DETECTION_RETENTION_DAYS`: Days to keep videos without detections

### Configuration Classes
All configuration is handled through dataclasses in `config/settings.py`:
- `CaptureConfig`: Camera and recording settings
- `MotionConfig`: Motion detection parameters
- `DetectionConfig`: AI detection settings
- `ProcessingConfig`: Processing server settings
- `SyncConfig`: File synchronization settings
- `WebConfig`: Web server settings

## Data Models

### Core Models (`core/models.py`)
- `VideoFile`: Represents recorded video segments
- `BirdDetection`: Individual detection results
- `MotionRegion`: Motion detection regions
- `ProcessingStats`: Processing statistics
- `SystemStatus`: System health information
- `CaptureSegment`: Video segment metadata

### Database Schema
- **Videos**: Video files with processing status
- **Detections**: AI detection results with bounding boxes
- **Settings**: User configuration (motion regions, thresholds)

## Key Features

### Motion Detection
- Background subtraction with adaptive learning
- Configurable regions of interest
- Contour filtering and area thresholds
- Motion timeout to prevent excessive recording
- Pre-motion buffer for capturing lead-up

### AI Detection
- Multi-class detection (birds, animals, people)
- Confidence thresholds per detection class
- Frame sampling for efficiency
- Clustering of related detections
- Thumbnail generation for positive detections

### Event Clustering
Detections are grouped into events based on:
- Time proximity (configurable window)
- Spatial proximity (bounding box distance)
- Species matching (same detection class)

### Web Interface
- **Pi Dashboard**: Live camera feed, motion settings, system status, system metrics
- **Processing Dashboard**: Detection results, processing stats, thumbnails, system metrics
- **Unified Dashboard**: Combined view of both systems with system metrics

## API Endpoints

### Pi Capture API (Port 8090)
- `GET /api/status`: System status and health
- `POST /api/motion-settings`: Update motion detection settings
- `GET /api/recent-videos`: Recent video recordings
- `GET /api/camera-feed`: Live camera stream
- `GET /api/system-metrics`: Real-time CPU, memory, disk usage

### Processing Server API (Port 8091)
- `GET /api/recent-detections`: Recent detections with clustering
- `GET /api/processing-stats`: Processing statistics
- `POST /api/process-video`: Manual video processing
- `GET /api/thumbnails/<path>`: Serve detection thumbnails
- `GET /api/system-metrics`: Real-time CPU, memory, disk usage

### Query Parameters
- `species`: Filter by detection class
- `start`/`end`: Date range filtering
- `sort`: Sort order (asc/desc)
- `limit`: Number of results

## File Organization

```
storage_path/
├── camera_0/             # Per-camera storage
│   ├── raw_footage/      # Recorded segments
│   ├── synced/           # Uploaded to server
│   └── capture.db        # Pi database
├── detections/           # Videos with animals
├── no_detections/        # Videos without animals
├── thumbnails/           # Detection thumbnails
└── processing.db         # Processing server database
```

## Common Development Tasks

### Adding New Detection Classes
1. Add to `DETECTION_CLASSES` environment variable
2. Add confidence threshold: `{CLASS}_CONFIDENCE=0.35`
3. Ensure AI model supports the class

### Modifying Motion Detection
- Update `MotionConfig` in `config/settings.py`
- Modify `MotionDetector` in `services/motion_detector.py`
- Update web interface in `web/routes/capture_routes.py`

### Adding New API Endpoints
- Add to appropriate route file in `web/routes/`
- Update Flask app factory in `web/app.py`
- Add frontend JavaScript in `web/static/js/`

### Database Schema Changes
- Modify repository classes in `database/repositories/`
- Add migration logic to repository `create_table()` methods
- Update data models in `core/models.py`

## Testing and Debugging

### Camera Testing
```bash
# Pi Camera
python3 -c "from picamera2 import Picamera2; print(Picamera2.global_camera_info())"

# USB Camera
ls /dev/video*
```

### Service Status
- Check web dashboards for system health
- Monitor logs for processing errors
- Use API endpoints to verify functionality

### Performance Optimization
- Adjust `PROCESS_EVERY_NTH_FRAME` for processing speed
- Use smaller AI models for faster inference
- Tune motion sensitivity to reduce false triggers

## Security Considerations

This is a defensive security and wildlife monitoring tool. When working with this code:

**Allowed:**
- Adding new detection classes
- Improving detection accuracy
- Performance optimizations
- Bug fixes
- Documentation improvements
- Security analysis of existing code

**Not Allowed:**
- Creating code that could be used maliciously
- Removing security features
- Adding backdoors or vulnerabilities

## Common Issues and Solutions

### Camera Not Available
- Ensure `--system-site-packages` for Pi Camera
- Check camera permissions and video group membership
- Verify camera hardware connection

### Blue/Distorted Colors
- System automatically converts RGB to BGR
- Update to latest version if issues persist

### Performance Issues
- Reduce frame processing frequency
- Use smaller AI models
- Adjust motion detection sensitivity

### File Sync Issues
- Check network connectivity
- Verify processing server is running
- Check disk space on both systems

## Dependencies

### Core Dependencies
- `torch>=2.1.0`: PyTorch for AI models
- `ultralytics>=8.1.0`: YOLOv5 implementation
- `opencv-python>=4.8.0`: Computer vision
- `flask>=2.3.0`: Web framework
- `numpy>=1.24.0`: Numerical computing
- `schedule>=1.2.0`: Task scheduling
- `psutil>=5.9.0`: System metrics collection

### System Dependencies
- `python3-picamera2`: Pi Camera interface (system package)
- `libcamera-apps`: Camera system libraries
- `ffmpeg`: Video processing (optional)

## Entry Points

### Starting the System
```bash
# Pi Capture System
python3 pi_capture/main.py

# AI Processing Server
python3 ai_processor/main.py
```

### Configuration Files
- `.env`: Environment variables
- `requirements.txt`: Python dependencies
- `setup_pi_camera.sh`: Automated Pi setup script

This context should help AI assistants understand the codebase structure, key components, and development patterns when working with the BirdCam project.