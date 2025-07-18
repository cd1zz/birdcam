# BirdCam Web Interface

Modern React-based web interface for the BirdCam wildlife detection system.

## Overview

This web UI provides:
- 📹 Live camera feeds from all connected cameras
- 🦅 Gallery of detected wildlife with thumbnails
- 📊 System analytics and statistics
- ⚙️ Configuration interface for motion and detection settings
- 👥 User management (admin/viewer accounts)
- 🌙 Dark mode support

## Quick Start

### Prerequisites
- Node.js 16+ and npm
- The AI Processing Server must be running
- The Raspberry Pi capture system must be running

### Installation

```bash
# Navigate to web-ui directory
cd web-ui

# Install dependencies
npm install

# Copy configuration
cp .env.example .env

# Edit configuration - IMPORTANT!
nano .env
```

### Configuration

Edit `.env` with your actual IP addresses:

```bash
# URL to Raspberry Pi capture system
VITE_PI_SERVER=http://192.168.1.50:8090

# URL to AI processing server (where this UI is served)
VITE_PROCESSING_SERVER=http://192.168.1.100:8091
```

**Important**: These URLs must be accessible from your browser, not just from the server.

### Development Mode

```bash
# Start development server with hot reload
npm run dev

# Access at http://localhost:5173
```

### Production Build

```bash
# Build optimized production version
npm run build

# Files are output to dist/ directory
# These are automatically served by the AI processor
```

### Deployment

The web UI is automatically served by the AI Processing Server at port 8091. Just build and the processor will serve the files.

## Features

### Live Feeds
- Real-time camera streams
- Motion indicator
- Camera status (active/passive)
- Snapshot capability

### Detections Gallery
- Thumbnail grid of all detections
- Filter by date, camera, species
- Video playback
- Detection confidence scores
- Download original videos

### Analytics (Admin Only)
- Detection statistics by species
- Camera activity heatmaps
- Storage usage monitoring
- Processing performance metrics

### Settings (Admin Only)
- Motion detection configuration
- Per-camera motion zones
- Detection class selection
- Confidence threshold adjustment
- User management

## Architecture

```
┌─────────────────┐
│   Web Browser   │
│                 │
│  React App      │
│  (This UI)      │
└────────┬────────┘
         │ HTTPS/HTTP
         │
    ┌────▼────┐
    │ Nginx/  │
    │ Proxy   │ (Optional)
    └────┬────┘
         │
┌────────▼────────┐        ┌─────────────┐
│ AI Processor    │        │ Raspberry   │
│ Port 8091       │◄──────►│ Pi          │
│                 │        │ Port 8090   │
│ - Serves UI     │        │             │
│ - API Backend   │        │ - Cameras   │
│ - Auth          │        │ - Streaming │
└─────────────────┘        └─────────────┘
```

## API Endpoints Used

### From Raspberry Pi (VITE_PI_SERVER):
- `/api/cameras` - List cameras
- `/api/camera/{id}/stream` - Live MJPEG stream
- `/api/camera/{id}/snapshot` - Single frame
- `/api/status` - System status

### From Processing Server (VITE_PROCESSING_SERVER):
- `/api/detections` - Detection results
- `/api/videos` - Video management
- `/api/analytics` - Statistics
- `/api/auth/*` - Authentication
- `/api/settings` - Configuration

## Troubleshooting

### "Cannot connect to camera system"
- Verify VITE_PI_SERVER URL is correct
- Check Pi system is running: `curl http://PI_IP:8090/api/status`
- Ensure no firewall blocking port 8090

### "Cannot connect to processing server"
- Verify VITE_PROCESSING_SERVER URL is correct
- Check processor is running: `curl http://PROCESSOR_IP:8091/api/health`
- Try rebuilding: `npm run build`

### "CORS errors in console"
- Ensure CORS_ENABLED=true in both .env files
- Check URLs don't have trailing slashes
- Verify you're accessing from correct domain

### "Login not working"
- Clear browser cache and localStorage
- Check browser console for specific errors
- Verify SECRET_KEY matches between systems

## Development

### Project Structure
```
src/
├── components/     # Reusable UI components
├── pages/         # Route pages
├── contexts/      # React contexts (auth, theme)
├── hooks/         # Custom React hooks
├── api/           # API client configuration
├── types/         # TypeScript type definitions
└── utils/         # Helper functions
```

### Key Technologies
- React 18 with TypeScript
- Vite for fast builds
- TailwindCSS for styling
- React Query for data fetching
- React Router for navigation
- Axios for API calls

### Testing
```bash
# Run linter
npm run lint

# Type checking
npm run type-check

# Build for production (validates everything)
npm run build
```

## Customization

### Changing Theme Colors
Edit `tailwind.config.js` to modify color scheme.

### Adding Detection Classes
1. Update DETECTION_CLASSES in processor's .env
2. Restart processor
3. UI will automatically show new classes

### Modifying Layouts
Components use TailwindCSS classes for styling. Edit component files directly.

## Security Notes

1. Initial admin setup requires local network access
2. All API calls use JWT authentication
3. Viewer accounts have read-only access
4. Admin features are route-protected

## Support

See main [Troubleshooting Guide](../docs/TROUBLESHOOTING.md) for system-wide issues.