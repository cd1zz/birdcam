# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a distributed bird/animal detection system with three main components:
- **Pi Capture** (Raspberry Pi): Motion-triggered video capture and segmentation
- **AI Processor** (Server): YOLO-based object detection on video segments
- **Web UI** (React/TypeScript): Live monitoring, results viewing, and system management

## Development Commands

### Backend (Python)
```bash
# Install dependencies
pip install -r requirements.txt
pip install -r tests/requirements.txt  # For testing

# Run services
python pi_capture/main.py     # On Raspberry Pi
python ai_processor/main.py   # On processing server

# Run tests
pytest                        # All tests
pytest tests/unit/           # Unit tests only
pytest tests/integration/    # Integration tests only
pytest -k "test_name"        # Specific test
pytest --cov=.              # With coverage
```

### Frontend (TypeScript/React)
```bash
cd web-ui

# Install dependencies
npm install

# Development
npm run dev                  # Start dev server (http://localhost:5173)
npm run lint                 # Run ESLint
npm run build               # Production build
npm run preview             # Preview production build
```

### Setup
```bash
# Copy and configure environment
cp .env.example .env
# Edit .env with your IP addresses and settings

# For Raspberry Pi camera setup
./setup_pi_camera.sh
```

## Architecture

### Key Directories
- `pi_capture/`: Raspberry Pi capture service
  - `camera_manager.py`: Multi-camera video capture with motion detection
  - `main.py`: Service entry point with sync to processor
- `ai_processor/`: Processing server
  - `processor.py`: YOLO detection pipeline
  - `main.py`: Service with Flask API
- `web/`: Flask API routes (used by both services)
- `services/`: Core business logic
  - `detection_service.py`: Detection result management
  - `storage_service.py`: File storage and cleanup
- `database/`: Repository pattern for data access
- `config/`: Configuration management
- `web-ui/`: React frontend application

### Data Flow
1. Pi cameras capture video → motion detection → segment into chunks
2. Segments sync to processing server every 15 minutes
3. Processor runs YOLO detection on each segment
4. Results stored in SQLite with detected/non-detected video separation
5. Web UI displays live feeds and historical detections

### Key Configuration
- Detection classes: bird, cat, dog, person, etc. (configurable in .env)
- Retention: 30 days for detections, 7 days for non-detections
- Motion detection uses background subtraction with configurable thresholds
- Pre-motion buffer captures 15 seconds before motion trigger

## Testing Approach

Tests use pytest with a clear unit/integration separation. When adding features:
- Unit tests go in `tests/unit/`
- Integration tests go in `tests/integration/`
- Mock external dependencies (cameras, filesystem) for unit tests
- Use `pytest -k` to run specific tests during development