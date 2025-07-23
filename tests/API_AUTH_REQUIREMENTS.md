# API Authentication Requirements

This document outlines the authentication requirements for all API endpoints in the BirdCam system.

## Authentication Methods

The system uses several authentication decorators:
- `@require_auth` - Requires valid JWT token
- `@require_auth_internal` - Requires valid JWT token + internal network IP
- `@require_admin` - Requires valid JWT token + admin role
- `@require_admin_internal` - Requires valid JWT token + admin role + internal network IP
- `@require_internal_network` - Only requires internal network IP (no auth token)

## Public Endpoints (No Authentication Required)

These endpoints can be accessed without any authentication:

- `GET /api/debug/simple` - Basic connectivity test
- `GET /api/debug/test` - Service verification
- `GET /api/setup/status` - Check if initial setup is required
- `POST /api/setup/create-admin` - Create first admin (internal network only)

## Authentication Endpoints

- `POST /api/auth/login` - Login with username/password
- `POST /api/auth/refresh` - Refresh access token using refresh token
- `POST /api/register` - Register new user (if enabled)
- `POST /api/verify-email` - Verify email with token
- `POST /api/resend-verification` - Resend verification email

## Protected Endpoints (Require Authentication)

### Standard User Access (`@require_auth`)
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/change-password` - Change password
- `GET /api/status` - System status
- `GET /api/recent-detections` - Recent wildlife detections
- `GET /api/system-metrics` - System performance metrics
- `POST /api/delete-detection` - Delete a detection
- `GET /videos/<filename>` - Stream video files
- `GET /thumbnails/<filename>` - Get detection thumbnails

### Internal Network + Auth (`@require_auth_internal`)
- `GET /api/motion-settings` - Get motion detection settings
- `GET /api/models/available` - List available AI models
- `GET /api/models/<model_id>/classes` - Get model detection classes

### Admin Only (`@require_admin`)
- `GET /api/admin/users` - List all users
- `POST /api/admin/users` - Create new user
- `PUT /api/admin/users/<user_id>` - Update user
- `DELETE /api/admin/users/<user_id>` - Delete user
- `GET /api/admin/logs` - View system logs
- `GET /api/admin/stats/system` - System statistics
- `GET /api/admin/stats/cameras` - Camera statistics

### Admin + Internal Network (`@require_admin_internal`)
- `POST /api/motion-settings` - Update motion settings
- `POST /api/process-now` - Trigger video processing
- `POST /api/cleanup-now` - Trigger cleanup
- `POST /api/reset-queue` - Reset processing queue
- `GET /api/system-settings` - Get system settings
- `POST /api/system-settings` - Update system settings

## Pi Camera Proxy Endpoints

These endpoints proxy requests to the Raspberry Pi camera system:

### With Authentication (`@require_auth`)
- `GET /api/pi/camera/<camera_id>/stream` - Live camera stream
- `GET /api/pi/camera/<camera_id>/snapshot` - Camera snapshot
- `GET /api/pi/status` - Pi system status
- `GET /api/pi/cameras` - List cameras
- `GET/POST /api/pi/motion-settings` - Motion settings
- `GET /api/pi/system-metrics` - Pi system metrics

### Admin Only
- `POST /api/pi/sync-now` - Force sync videos
- `POST /api/pi/process-server-queue` - Process queue

## Email System Endpoints (Admin Only)

All email-related endpoints require admin role:
- `POST /api/admin/email/test` - Send test email
- `GET/PUT /api/admin/settings/email` - Email configuration
- `GET/PUT /api/admin/settings/registration` - Registration settings
- `GET/PUT /api/admin/email/templates/<type>` - Email templates
- `POST /api/admin/email/send-invite` - Send registration invite

## Registration System

- `POST /api/admin/registration/generate-link` - Generate invite link (admin)
- `GET /api/admin/registration/links` - List invite links (admin)
- `DELETE /api/admin/registration/links/<id>` - Delete invite link (admin)
- `GET /api/admin/registration/pending` - List pending registrations (admin)
- `POST /api/admin/registration/verify/<user_id>` - Manually verify user (admin)

## Log Viewing Endpoints

- `GET /api/logs/pi-capture` - Pi capture logs (auth required)
- `GET /api/logs/ai-processor` - AI processor logs (auth required)
- `GET /api/logs/combined` - Combined logs (auth required)
- `GET /api/logs/levels` - Log levels (auth required)
- `GET /api/logs/export` - Export logs (auth required)

## Notes

1. **Internal Network IPs**: Defined in configuration, typically includes:
   - 127.0.0.1 (localhost)
   - 192.168.x.x (local network)
   - 10.x.x.x (local network)

2. **JWT Tokens**: 
   - Access tokens expire after a configured time (default 1 hour)
   - Refresh tokens have longer expiry (default 30 days)
   - Tokens must be sent in Authorization header: `Bearer <token>`

3. **Registration Modes**:
   - `disabled` - No new registrations
   - `open` - Anyone can register
   - `invite` - Requires invitation link

4. **Error Responses**:
   - 401 Unauthorized - No valid token or token expired
   - 403 Forbidden - Valid token but insufficient permissions
   - 400 Bad Request - Invalid request data