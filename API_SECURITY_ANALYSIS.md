# BirdCam API Security Analysis Report

## Overview
This report analyzes all API endpoints in the BirdCam project to identify authentication requirements and potential security concerns.

## Authentication Decorators Used
- `@require_auth` - Requires valid JWT token
- `@require_admin` - Requires admin role (includes auth check)
- `@require_auth_with_query` - Accepts token in header or query param (for streaming)
- `@require_internal_network` - Restricts to local network IPs
- `@require_admin_internal` - Combines admin + internal network checks

## Endpoint Security Analysis

### 1. **UNAUTHENTICATED ENDPOINTS** (Publicly Accessible)

#### Critical Security Concern - These endpoints have NO authentication:

**Setup Routes** (`/web/routes/setup_routes.py`):
- `GET /status` - Shows if setup is required (reveals admin exists)
- `POST /create-admin` - Creates first admin (internal network only)

**Registration Routes** (`/web/routes/registration_routes.py`):
- `POST /api/register` - User registration (controlled by REGISTRATION_MODE)
- `POST /api/verify-email` - Email verification
- `POST /api/resend-verification` - Resend verification email

**Auth Routes** (`/web/routes/auth_routes.py`):
- `POST /login` - User login (returns JWT tokens)
- `POST /refresh` - Refresh tokens

**Capture Routes** (`/web/routes/capture_routes.py` - Pi System):
- `GET /` - Status page
- `GET /api/status` - System status
- `GET /api/server-status` - Server connection status
- `POST /api/sync-now` - Trigger sync
- `GET /api/server-detections` - Get detections from server
- `GET /api/server-metrics` - Get server metrics
- `POST /api/delete-detection` - Delete detection
- `GET /api/motion-settings` - Get motion settings
- `GET /api/motion-debug` - Motion detection debug info
- `POST /api/motion-settings` - Set motion settings
- `POST /api/process-server-queue` - Trigger processing
- `GET /api/health` - Health check
- `GET /videos/<filename>` - Serve videos
- `GET /thumbnails/<filename>` - Serve thumbnails
- `GET /api/cameras` - List cameras
- `GET /api/active-passive/stats` - Camera stats
- `GET /api/active-passive/config` - Camera config
- `GET /api/active-passive/test-trigger` - Test trigger
- `GET /api/system-metrics` - System metrics
- `GET /api/camera/<camera_id>/stream` - Live camera stream
- `GET /api/camera/<camera_id>/snapshot` - Camera snapshot
- `GET /api/statistics/summary` - System statistics

**Processing Routes** (`/web/routes/processing_routes.py`):
- `GET /` - Serve UI
- `GET /<path>` - Serve UI assets
- `POST /upload` - Upload video (NO AUTH!)
- `GET /api/debug/simple` - Debug endpoint
- `GET /api/debug/test` - Test endpoint
- `GET /videos/<filename>` - Serve videos
- `GET /thumbnails/<filename>` - Serve thumbnails

### 2. **AUTHENTICATED ENDPOINTS** (Require Login)

**Auth Routes**:
- `GET /me` - Get current user (@require_auth)
- `POST /change-password` - Change password (@require_auth)

**Processing Routes**:
- `GET /api/status` - System status (@require_auth)
- `GET /api/recent-detections` - Recent detections (@require_auth)
- `POST /api/process-now` - Process videos (@require_auth)
- `POST /api/delete-detection` - Delete detection (@require_auth)
- `GET /api/models/available` - Available models (@require_auth)
- `GET /api/models/<model_id>/classes` - Model classes (@require_auth)

**Pi Proxy Routes** (All require auth):
- `GET /api/pi/camera/<camera_id>/stream` - Camera stream (@require_auth_with_query)
- `GET /api/pi/camera/<camera_id>/snapshot` - Camera snapshot (@require_auth_with_query)
- `GET /api/pi/status` - Pi status (@require_auth)
- `GET /api/pi/cameras` - Camera list (@require_auth)
- `GET/POST /api/pi/motion-settings` - Motion settings (@require_auth)
- `GET /api/pi/motion-debug` - Motion debug (@require_auth)
- `POST /api/pi/sync-now` - Sync trigger (@require_auth)
- `POST /api/pi/process-server-queue` - Process queue (@require_auth)
- `GET /api/pi/system-metrics` - System metrics (@require_auth)
- `GET /api/pi/active-passive/stats` - Camera stats (@require_auth)
- `GET /api/pi/active-passive/test-trigger` - Test trigger (@require_auth)

**API Discovery Routes**:
- `GET /api/discovery/routes` - List all routes (@require_auth)
- `POST /api/discovery/validate` - Validate routes (@require_auth)
- `GET /api/discovery/openapi` - OpenAPI spec (@require_auth)

**Admin Routes** (Basic info):
- `GET /api/admin/settings/system` - System settings (@require_auth)
- `GET /api/admin/stats/cameras` - Camera stats (@require_auth)

### 3. **ADMIN-ONLY ENDPOINTS** (Require Admin Role)

**Processing Routes**:
- `POST /api/cleanup-now` - Cleanup videos (@require_admin)
- `POST /api/reset-queue` - Reset queue (@require_admin)

### 4. **ADMIN + INTERNAL NETWORK ENDPOINTS** (Most Restrictive)

**Registration Routes**:
- `POST /api/admin/registration/generate-link` - Generate invite (@require_admin_internal)
- `GET /api/admin/registration/links` - List invites (@require_admin_internal)
- `DELETE /api/admin/registration/links/<id>` - Delete invite (@require_admin_internal)
- `GET /api/admin/registration/pending` - Pending users (@require_admin_internal)
- `POST /api/admin/registration/verify/<id>` - Verify user (@require_admin_internal)
- `POST /api/admin/email/test` - Test email (@require_admin_internal)
- `GET /api/admin/settings/email` - Email settings (@require_admin_internal)
- `PUT /api/admin/settings/email` - Update email (@require_admin_internal)
- `GET /api/admin/settings/registration` - Registration settings (@require_admin_internal)
- `PUT /api/admin/settings/registration` - Update registration (@require_admin_internal)
- `GET /api/admin/email/templates` - Email templates (@require_admin_internal)
- `GET/PUT /api/admin/email/templates/<type>` - Manage templates (@require_admin_internal)
- `POST /api/admin/email/templates/<type>/reset` - Reset template (@require_admin_internal)
- `POST /api/admin/email/templates/<type>/preview` - Preview template (@require_admin_internal)
- `POST /api/admin/email/send-invite` - Send invite (@require_admin_internal)

**Processing Routes**:
- `GET /api/motion-settings` - Motion settings (@require_auth_internal)
- `POST /api/motion-settings` - Update motion (@require_admin_internal)
- `GET /api/system-metrics` - System metrics (@require_auth_internal)
- `GET /api/system-settings` - System settings (@require_auth_internal)
- `POST /api/system-settings` - Update system (@require_admin_internal)

**Pi Proxy Routes**:
- `GET /api/pi/active-passive/config` - Camera config (@require_auth_internal)

**Log Routes**:
- `GET /api/logs/pi-capture` - Pi logs (@require_admin_internal)
- `GET /api/logs/ai-processor` - AI logs (@require_admin_internal)
- `GET /api/logs/combined` - Combined logs (@require_admin_internal)
- `GET /api/logs/levels` - Log levels (@require_admin_internal)
- `GET /api/logs/remote/pi-capture` - Remote Pi logs (@require_admin_internal)
- `GET /api/logs/export` - Export logs (@require_admin_internal)

**Admin Routes**:
- `GET /api/admin/users` - List users (@require_admin_internal)
- `POST /api/admin/users` - Create user (@require_admin_internal)
- `PUT /api/admin/users/<id>` - Update user (@require_admin_internal)
- `DELETE /api/admin/users/<id>` - Delete user (@require_admin_internal)
- `GET /api/admin/logs` - Get logs (@require_admin_internal)
- `GET /api/admin/logs/files` - Log files (@require_admin_internal)
- `GET /api/admin/logs/capture` - Capture logs (@require_admin_internal)
- `GET /api/admin/logs/download/<file>` - Download log (@require_admin_internal)
- `POST /api/admin/logs/clear` - Clear logs (@require_admin_internal)
- `POST /api/admin/settings/system` - Update settings (@require_admin_internal)
- `GET /api/admin/stats/system` - System stats (@require_admin_internal)

## CRITICAL SECURITY CONCERNS

### 1. **Completely Unprotected Endpoints on Pi Capture System**
The entire Pi capture system (`/web/routes/capture_routes.py`) has NO authentication on any endpoints. This means anyone who can reach the Pi's IP address can:
- View live camera streams
- Change motion detection settings
- Delete detections
- Trigger sync operations
- Access system metrics

### 2. **Unprotected Video Upload Endpoint**
`POST /upload` in processing routes has NO authentication. Anyone can upload arbitrary video files to the system.

### 3. **Unprotected Media Files**
Video and thumbnail files are served without authentication checks:
- `/videos/<filename>`
- `/thumbnails/<filename>`

### 4. **Information Disclosure**
Several endpoints leak sensitive information without authentication:
- System status and metrics
- Camera configurations
- Server connection status

## RECOMMENDATIONS

### Immediate Actions Required:
1. **Add authentication to Pi capture endpoints** - All API endpoints should require at least basic authentication
2. **Protect the upload endpoint** - Add @require_auth to POST /upload
3. **Secure media file access** - Add authentication checks for video/thumbnail serving
4. **Review registration flow** - Ensure registration endpoints respect REGISTRATION_MODE setting

### Best Practices:
1. Use the processing server's authenticated proxy endpoints (`/api/pi/*`) instead of direct Pi access
2. Implement rate limiting on public endpoints
3. Add CORS headers to restrict API access to authorized origins
4. Log all authentication failures and unauthorized access attempts
5. Consider implementing API keys for service-to-service communication

### Architecture Recommendation:
The Pi capture system should not expose any endpoints directly. All access should go through the authenticated processing server proxy endpoints. This provides a single security boundary and consistent authentication across the system.