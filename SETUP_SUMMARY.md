# BirdCam Setup Summary

## 🎯 What You Need

Two separate computers:
1. **Raspberry Pi** - Captures video from cameras
2. **Processing Server** - Runs AI detection and web interface

## 🚀 Setup Order

### 1️⃣ Set Up Raspberry Pi First
```bash
cd birdcam
cp .env.pi.example .env.pi
nano .env.pi  # Set PROCESSING_SERVER to your AI server's IP!
pip install -r requirements.pi.txt
python pi_capture/main.py
```

### 2️⃣ Set Up Processing Server
```bash
cd birdcam
cp .env.processor.example .env.processor
pip install -r requirements.processor.txt
python ai_processor/main.py
```

### 3️⃣ Build Web Interface (on processor)
```bash
cd web-ui
cp .env.example .env
nano .env  # Set both Pi and Processor IPs
npm install
npm run build
```

### 4️⃣ Create Admin Account
- Open browser to `http://PROCESSOR_IP:8091`
- You'll see the setup page
- Create admin (must be on local network)

## 📁 Configuration Files

| System | Config File | Key Setting |
|--------|------------|-------------|
| Pi | `.env.pi` | `PROCESSING_SERVER=` (AI server IP) |
| Processor | `.env.processor` | Detection settings |
| Web UI | `web-ui/.env` | Both system URLs |

## 🔍 Quick Checks

```bash
# Is Pi running?
curl http://PI_IP:8090/api/status

# Is Processor running?
curl http://PROCESSOR_IP:8091/api/health

# Can Pi reach Processor?
# From Pi: curl http://PROCESSOR_IP:8091/api/health
```

## 📖 Detailed Guides

- [Full README](README.md)
- [Pi Setup](docs/PI_SETUP.md)
- [Processor Setup](docs/PROCESSOR_SETUP.md)
- [Configuration](docs/CONFIGURATION.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

## 🆘 Common Issues

1. **"No camera"** → Run `./setup_pi_camera.sh` on Pi
2. **"Can't connect"** → Check PROCESSING_SERVER IP in `.env.pi`
3. **"No detections"** → Lower confidence values in `.env.processor`
4. **"Slow processing"** → Use `MODEL_NAME=yolov5n` for speed

Remember: Pi and Processor must be on same network and able to reach each other!