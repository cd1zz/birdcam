# Docker Deployment Guide for BirdCam

## Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/your-username/birdcam.git
cd birdcam
```

### 2. Build the frontend (required for processor)
```bash
cd web-ui
npm install
npm run build
cd ..
```

### 3. Configure environment
```bash
cp .env.docker.example .env
# Edit .env with your settings
```

### 4. Run with Docker Compose
```bash
# Build and start both services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

The web interface will be available at: http://localhost:5001

## Running Components Separately

### On Processing Server Only
```bash
# Build processor image
docker build -f Dockerfile.processor -t birdcam-processor .

# Run processor
docker run -d \
  -p 5001:5001 \
  -v $(pwd)/bird_footage:/app/bird_footage \
  -e SECRET_KEY=your-secret-key \
  -e ADMIN_PASSWORD=your-password \
  birdcam-processor
```

### On Raspberry Pi Only
```bash
# Build capture image
docker build -f Dockerfile.capture -t birdcam-capture .

# Run capture (with camera access)
docker run -d \
  -p 8090:8090 \
  --device /dev/video0:/dev/video0 \
  -v $(pwd)/bird_footage:/app/bird_footage \
  -e PROCESSING_SERVER=http://your-processor-ip:5001 \
  -e SECRET_KEY=your-secret-key \
  birdcam-capture
```

## Architecture Options

### Option 1: All-in-One (Testing/Development)
Run both services on the same machine using docker-compose.yml

### Option 2: Split Deployment (Production)
- Run capture container on Raspberry Pi
- Run processor container on powerful server
- Configure PROCESSING_SERVER and CAPTURE_SERVER environment variables

### Option 3: Hybrid
- Run capture natively on Pi (using systemd)
- Run processor in Docker on server

## Using Pre-built Images

Once the GitHub Actions workflow succeeds, you can use pre-built images:

```bash
# Pull from GitHub Container Registry
docker pull ghcr.io/your-username/birdcam-processor:latest
docker pull ghcr.io/your-username/birdcam-capture:latest

# Run with pre-built images
docker run -d \
  -p 5001:5001 \
  -v $(pwd)/bird_footage:/app/bird_footage \
  ghcr.io/your-username/birdcam-processor:latest
```

## Troubleshooting

### Camera Access Issues
- Linux: Ensure user is in `video` group: `sudo usermod -a -G video $USER`
- May need to run with `--privileged` flag for some cameras
- Check camera device: `ls -la /dev/video*`

### Permission Issues
- Ensure volumes have correct permissions
- Run `chmod -R 777 bird_footage` if needed (not recommended for production)

### Memory Issues
- YOLO models require significant RAM
- Ensure Docker has enough memory allocated
- Consider using lighter models (yolov5n instead of yolov5s)

## Environment Variables

See `.env.docker.example` for all available configuration options.

Key variables:
- `SECRET_KEY`: Must be same on both services
- `ADMIN_PASSWORD`: First-time admin setup
- `CAMERA_0_TYPE`: Camera type (opencv/picamera2)
- `PROCESSING_SERVER`: Where capture sends videos
- `CAPTURE_SERVER`: Where processor fetches from Pi