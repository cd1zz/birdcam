# BirdCam - Distributed Wildlife Detection System

A two-system architecture for wildlife detection: Raspberry Pi cameras capture video, and a separate AI server processes it.

![System Overview](docs/images/image.png)
![Detection Gallery](docs/images/image-1.png)

## 🏗️ System Architecture

BirdCam uses a **two-system design** for flexibility and performance:

```
┌─────────────────────┐                    ┌─────────────────────┐
│   RASPBERRY PI      │                    │   AI PROCESSING     │
│                     │                    │      SERVER         │
│  • Camera capture   │     Network        │  • YOLO detection   │
│  • Motion detection │ ◄────────────────► │  • Video storage    │
│  • Video streaming  │    Sync videos     │  • Web interface    │
│  • Basic web API    │                    │  • User management  │
└─────────────────────┘                    └─────────────────────┘
         ▲                                           ▲
         │                                           │
         └─────────────────┬─────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │ WEB BROWSER │
                    │             │
                    │ • Live view │
                    │ • Settings  │
                    └─────────────┘
```

### System 1: Raspberry Pi (Camera Capture)
- **Purpose**: Capture video from cameras
- **Runs**: `pi_capture/main.py`
- **Features**: Motion detection, multi-camera support, video buffering
- **Config**: Uses `.env.pi` (renamed from `.env`)

### System 2: AI Processing Server (Any Linux/Windows/Mac)
- **Purpose**: Process videos with AI, serve web interface
- **Runs**: `ai_processor/main.py`
- **Features**: YOLO detection, video storage, web UI, user management
- **Config**: Uses `.env.processor` (renamed from `.env`)

## 🚀 Quick Start Guide

### Step 1: Choose Your Setup

You need TWO separate machines:
1. **Raspberry Pi** with camera(s) attached
2. **Processing Server** (can be any computer with decent CPU/GPU)

### Step 2: Set Up the Raspberry Pi

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/birdcam.git
cd birdcam

# 2. Create Pi-specific configuration
cp config/examples/.env.pi.example .env.pi
nano .env.pi

# 3. Edit these key settings:
PROCESSING_SERVER=192.168.1.100  # IP of your AI server
CAMERA_IDS=0                     # Your camera ID(s)

# 4. Install dependencies
pip install -r requirements.pi.txt

# 5. Setup camera permissions
./scripts/setup/setup_pi_camera.sh

# 6. Install and start capture service
sudo ./scripts/setup/install_pi_capture_service.sh
sudo systemctl start pi-capture.service

# Or run manually for testing:
# python pi_capture/main.py
```

### Step 3: Set Up the AI Processing Server

```bash
# 1. Clone the repository (on your processing server)
git clone https://github.com/yourusername/birdcam.git
cd birdcam

# 2. Create processor-specific configuration
cp config/examples/.env.processor.example .env.processor
nano .env.processor

# 3. Edit settings (most defaults are fine)
# IMPORTANT: If exposing to internet, add:
CAPTURE_SERVER=192.168.1.50      # Your Pi's internal IP
CAPTURE_PORT=8090               # Pi's port
SECRET_KEY=<generate-secure-key>

# 4. Install dependencies
pip install -r requirements.processor.txt

# 5. Install and start AI processor service
sudo ./scripts/setup/install_ai_processor_service.sh
sudo systemctl start ai-processor.service

# Or run manually for testing:
# python ai_processor/main.py

# 6. Set up web UI
cd web-ui
# For local network:
cp ../config/examples/.env.web-ui.example .env
# For internet access (secure proxy):
cp ../config/examples/.env.proxy.example .env

nano .env  # Update with your server IPs
npm install
npm run build
```

### Step 4: Initial Admin Setup

1. Open web browser to: `http://YOUR_PROCESSOR_IP:8091`
2. You'll be redirected to `/setup` automatically
3. Create your admin account (must be on local network)
4. Start using the system!

## 📋 Configuration Files

See [Environment Files Guide](docs/ENV_FILES_GUIDE.md) for detailed configuration instructions.

### Quick Reference:
- **`.env.pi`** - Raspberry Pi settings (cameras, motion detection)
- **`.env.processor`** - AI server settings (detection, storage, proxy)
- **`web-ui/.env`** - Frontend configuration (server URLs)

### Internet Access (Recommended Setup):
Use the secure proxy mode to expose only one server:
```bash
# In .env.processor:
CAPTURE_SERVER=192.168.1.50  # Pi's internal IP
SECRET_KEY=<secure-key>

# In web-ui/.env:
VITE_PROCESSING_SERVER=https://your-tunnel.com
VITE_PI_SERVER=              # Leave empty for proxy mode
```

## 🎥 Multi-Camera Support

- **Camera 0**: Active camera (performs motion detection)
- **Camera 1+**: Passive cameras (record when Camera 0 detects motion)
- All cameras record synchronized video from different angles

## 🔧 Managing Services

### Systemd Service Commands

Once installed, use these commands to manage the services:

**On Raspberry Pi:**
```bash
# Start/stop/restart service
sudo systemctl start pi-capture.service
sudo systemctl stop pi-capture.service
sudo systemctl restart pi-capture.service

# Check service status
sudo systemctl status pi-capture.service

# View logs
journalctl -u pi-capture.service -f

# Enable/disable auto-start on boot
sudo systemctl enable pi-capture.service
sudo systemctl disable pi-capture.service
```

**On AI Processing Server:**
```bash
# Start/stop/restart service
sudo systemctl start ai-processor.service
sudo systemctl stop ai-processor.service
sudo systemctl restart ai-processor.service

# Check service status
sudo systemctl status ai-processor.service

# View logs
journalctl -u ai-processor.service -f

# Enable/disable auto-start on boot
sudo systemctl enable ai-processor.service
sudo systemctl disable ai-processor.service
```

### Troubleshooting Services

If a service fails to start:
1. Check logs: `journalctl -u <service-name> -n 50`
2. Verify virtual environment: Ensure `.venv` exists and has all dependencies
3. Check permissions: Service runs as configured user (default: pi/craig)
4. Validate .env file: Ensure all required settings are present

## 🔧 Detailed Setup Guides

- [Raspberry Pi Setup Guide](docs/PI_SETUP.md)
- [Processing Server Setup Guide](docs/PROCESSOR_SETUP.md)
- [Environment Files Guide](docs/ENV_FILES_GUIDE.md)
- [Secure Proxy Setup](docs/SECURE_PROXY_SETUP.md)
- [Configuration Reference](docs/CONFIGURATION.md)
- [Troubleshooting Guide](docs/TROUBLESHOOTING.md)

## 📊 Features

- **Real-time Monitoring**: Live camera feeds from all cameras
- **AI Detection**: Identifies birds, cats, dogs, and more
- **Smart Storage**: Keeps detections for 30 days, others for 7
- **Web Interface**: Modern React UI with dark mode
- **User Management**: Admin and viewer accounts
- **Motion Zones**: Configure detection regions per camera
- **Access Logging**: HTTP request logging to syslog/journald
- **System Logs**: Admin users can view logs from both services in the web UI (requires systemd service installation)

## 🛠️ Development

```bash
# Run tests
pytest

# Development mode
cd web-ui && npm run dev

# Build for production
cd web-ui && npm run build
```

## 📝 License

MIT License - see LICENSE file

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## ❓ Support

- Check [Troubleshooting Guide](docs/TROUBLESHOOTING.md)
- Open an issue on GitHub
- Include logs and configuration details