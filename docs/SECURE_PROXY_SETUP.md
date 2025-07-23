# Secure Proxy Setup for Internet Access

This guide explains how to securely expose your bird camera system to the internet using only one CloudFlare tunnel.

## Overview

Instead of exposing both the Pi and AI Processor to the internet, this setup:
- Only exposes the AI Processor (which has authentication)
- Proxies Pi camera requests through the AI Processor
- Enforces authentication for all camera access
- Requires only one CloudFlare tunnel

## Architecture

```
Internet → CloudFlare Tunnel → AI Processor (Auth) → Internal Pi
                                    ↓
                                 Web UI
```

## Setup Steps

### 1. Configure the AI Processor

Edit your `.env.processor` file to include the Pi server details:

```bash
# Pi Capture Server (for proxy endpoints)
CAPTURE_SERVER=192.168.1.100    # Your Pi's IP address
CAPTURE_PORT=8090               # Port Pi is running on
```

### 2. Configure the Web UI

Copy the proxy configuration example:

```bash
cd web-ui
cp ../config/examples/.env.proxy.example .env
```

Edit `.env` to set your CloudFlare tunnel URL:

```bash
# Processing Server URL (your CloudFlare tunnel)
VITE_PROCESSING_SERVER=https://your-tunnel.trycloudflare.com

# Leave PI_SERVER empty to enable proxy mode
VITE_PI_SERVER=
```

### 3. Build and Deploy the Web UI

```bash
cd web-ui
npm run build
```

The built files will be served by the AI Processor.

### 4. Set Up CloudFlare Tunnel

Create a tunnel that points to your AI Processor:

```bash
# On the AI Processor machine
cloudflared tunnel create birdcam
cloudflared tunnel route dns birdcam birdcam.yourdomain.com
cloudflared tunnel run --url http://localhost:8091 birdcam
```

### 5. Verify Security

With this setup:
- Pi camera endpoints require authentication
- Only one server exposed to internet
- All camera streams are proxied securely
- JWT tokens protect all sensitive endpoints

## API Endpoints

The AI Processor now provides these proxy endpoints:

### Camera Access (Authenticated)
- `/api/pi/camera/{id}/stream` - Live camera stream
- `/api/pi/camera/{id}/snapshot` - Camera snapshot
- `/api/pi/cameras` - List cameras
- `/api/pi/status` - Pi system status

### Motion Settings (Authenticated)
- `/api/pi/motion-settings` - Get/Set motion detection settings
- `/api/pi/motion-debug` - Motion detection debug info

### System Control (Authenticated)
- `/api/pi/sync-now` - Trigger video sync
- `/api/pi/process-server-queue` - Trigger processing
- `/api/pi/system-metrics` - Pi system metrics

## Authentication Details

The proxy endpoints support two authentication methods:

1. **Header-based** (for API calls): `Authorization: Bearer <token>`
2. **Query parameter** (for streams): `?token=<token>`

The Web UI automatically appends the token to stream URLs when in proxy mode.

## Troubleshooting

### "Failed to connect to Pi camera"
- Check `CAPTURE_SERVER` and `CAPTURE_PORT` in `.env.processor`
- Ensure Pi is accessible from AI Processor: `curl http://192.168.1.100:8090/api/status`

### Authentication errors (401)
- Ensure you're logged into the Web UI
- Check if token exists: Open browser console and run `localStorage.getItem('accessToken')`
- Try logging out and back in to refresh the token
- Verify `SECRET_KEY` is set in `.env.processor`

### Camera stream not loading
- Check browser console for errors
- Verify the stream URL includes token parameter
- Test with curl: `curl "https://your-tunnel.com/api/pi/camera/0/snapshot?token=YOUR_TOKEN"`
- Check if direct Pi access works from AI Processor: `curl http://192.168.1.100:8090/api/camera/0/snapshot`

## Benefits

1. **Single Entry Point**: Only one CloudFlare tunnel needed
2. **Enhanced Security**: All Pi endpoints now require authentication
3. **Simplified Configuration**: Web UI only needs one server URL
4. **No Pi Exposure**: Pi remains completely internal
5. **Centralized Auth**: All authentication handled by AI Processor

## Rollback

To switch back to direct Pi access:
1. Set `VITE_PI_SERVER` in `web-ui/.env`
2. Create a second CloudFlare tunnel for the Pi
3. Rebuild and deploy the Web UI