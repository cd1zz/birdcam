# 🐦 BirdCam - AI-Powered Wildlife Detection System

BirdCam is a comprehensive wildlife detection system that combines motion detection, AI-powered bird/animal recognition, and automated video processing. It's designed to run on Raspberry Pi devices for capture and a processing server for AI analysis.

## 🎯 Features

- **Motion Detection**: Intelligent motion detection with configurable regions and thresholds
- **Multi-Camera Support**: Support for multiple cameras (Pi Camera, USB cameras)
- **AI Bird/Animal Detection**: Uses YOLOv5 for accurate wildlife detection
- **Automated Processing**: Scheduled video processing and cleanup
- **Web Dashboard**: Unified dashboard for monitoring both capture and processing
- **Event Clustering**: Groups related detections into single events
- **Configurable Retention**: Different retention policies for videos with/without detections
- **Thumbnail Generation**: Automatic thumbnail creation for detected animals

## 🏗️ Architecture

### Two-Component System:
1. **Pi Capture System** (`pi_capture/main.py`): Motion detection and video recording
2. **AI Processing Server** (`ai_processor/main.py`): AI analysis and detection clustering

### Key Components:
- **Motion Detection**: Background subtraction with configurable regions
- **Video Processing**: Segment-based recording with motion triggers
- **AI Detection**: Multi-class detection (birds, animals) with confidence thresholds
- **File Sync**: Automated transfer from Pi to processing server
- **Web Interface**: Real-time status monitoring and configuration

## 🚀 Quick Start

### Pi Camera Setup (Recommended)
```bash
# Run automated setup
chmod +x setup_pi_camera.sh
./setup_pi_camera.sh

# Manual setup if needed
sudo raspi-config  # Enable camera
sudo apt install -y python3-picamera2 libcamera-apps
python3 -m venv .venv --system-site-packages
source .venv/bin/activate
pip install -r requirements.txt
```

### USB Camera Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configuration
```bash
cp .env.example .env
# Edit .env with your settings
```

### Running the System

**Pi Capture System:**
```bash
python3 pi_capture/main.py
```

**AI Processing Server:**
```bash
python3 ai_processor/main.py
```

## 📊 Web Dashboard

Access the unified dashboard at `http://your-pi-ip:8090`

### Features:
- Live camera feed with motion detection overlay
- Real-time detection statistics
- Processing queue status
- Motion settings configuration (saved automatically)
- Recent detections with thumbnails
- System health monitoring

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CAMERA_IDS` | auto-detect | Comma-separated camera IDs |
| `STORAGE_PATH` | `./bird_footage` | Base storage directory |
| `PROCESSING_SERVER` | `192.168.1.136` | Processing server IP |
| `DETECTION_CLASSES` | `bird` | Detection classes |
| `MODEL_NAME` | `yolov5n` | AI model |
| `MOTION_THRESHOLD` | `5000` | Motion detection sensitivity |
| `SEGMENT_DURATION` | `300` | Video segment length (seconds) |
| `DETECTION_RETENTION_DAYS` | `30` | Keep detection videos |
| `NO_DETECTION_RETENTION_DAYS` | `7` | Keep non-detection videos |

### Detection Classes
Supports multiple detection classes with individual confidence thresholds:
```bash
DETECTION_CLASSES=bird,cat,dog,person
BIRD_CONFIDENCE=0.35
CAT_CONFIDENCE=0.40
DOG_CONFIDENCE=0.45
```

## 🎛️ Motion Detection

### Features:
- **Background Subtraction**: Adaptive background learning
- **Region of Interest**: Configurable detection zones
- **Contour Filtering**: Minimum area thresholds
- **Motion Timeout**: Prevents excessive recording
- **Pre-motion Buffer**: Captures seconds before motion

### Configuration:
- Motion regions are saved automatically via web interface
- Thresholds adjustable in real-time
- Visual feedback through web dashboard

## 🤖 AI Detection

### Supported Models:
- YOLOv5 (nano, small, medium, large)
- Custom confidence thresholds per class
- Frame sampling for efficiency

### Detection Pipeline:
1. Video segments uploaded to processing server
2. AI model analyzes frames at intervals
3. Detections clustered by time and location
4. Thumbnails generated for positive detections
5. Results stored in database

## 📁 File Organization

```
storage_path/
├── camera_0/
│   ├── raw_footage/     # Recorded segments
│   ├── synced/          # Uploaded to server
│   └── capture.db       # Pi database
├── detections/          # Videos with animals
├── no_detections/       # Videos without animals
├── thumbnails/          # Detection thumbnails
└── processing.db        # Processing server database
```

## 🔧 API Endpoints

### Pi Capture API (Port 8090)
- `GET /api/status` - System status
- `POST /api/motion-settings` - Update motion settings
- `GET /api/recent-videos` - Recent recordings

### Processing Server API (Port 8091)
- `GET /api/recent-detections` - Recent detections with clustering
- `GET /api/processing-stats` - Processing statistics
- `POST /api/process-video` - Manual video processing

### Query Parameters:
```bash
# Filter by species and date
/api/recent-detections?species=bird&start=2025-01-01&end=2025-01-31

# Sort and limit results
/api/recent-detections?sort=desc&limit=50
```

## 🔄 Event Clustering

Detections are intelligently grouped into events based on:
- **Time proximity**: Detections within configurable time window
- **Spatial proximity**: Distance between bounding box centers
- **Species matching**: Same detection class

This prevents dashboard spam from the same visitor and provides more meaningful statistics.

## 🧹 Maintenance

### Automated Cleanup:
- **Pi**: Old synced files cleaned up daily
- **Server**: Videos cleaned based on retention policies
- **Scheduling**: Configurable cleanup schedules

### Manual Cleanup:
```bash
python3 clean_files.py
```

## 🚨 Troubleshooting

### Camera Issues:
```bash
# Check camera detection
python3 -c "from picamera2 import Picamera2; print(Picamera2.global_camera_info())"

# USB camera check
ls /dev/video*
```

### Permission Issues:
```bash
sudo usermod -a -G video $USER
# Log out and back in
```

### Blue/Distorted Colors:
- Updated versions automatically convert RGB to BGR
- Ensure you're running the latest code

### Performance Issues:
- Reduce `PROCESS_EVERY_NTH_FRAME` for faster processing
- Use smaller model (`yolov5n` vs `yolov5s`)
- Adjust motion sensitivity to reduce false triggers

## 📈 System Requirements

### Pi Capture:
- Raspberry Pi 3B+ or newer
- Pi Camera Module or USB camera
- 16GB+ SD card
- Network connection

### Processing Server:
- Python 3.8+
- 4GB+ RAM
- GPU optional (CUDA support)
- Network connection

## 🤝 Contributing

This is a defensive security and wildlife monitoring tool. Contributions welcome for:
- New detection classes
- Performance improvements
- Bug fixes
- Documentation improvements

## 📄 License

Open source - see individual files for specific licensing information.