# BirdCam Codebase Audit

**Date:** 2026-04-06
**Scope:** Full codebase analysis — architecture, security, bugs, tests, configuration

## Architecture Assessment

**Rating: Good foundation, needs security hardening**

The two-system design (Raspberry Pi capture + AI processing server) is well-structured with clean separation of concerns: repository pattern for data access, services layer for business logic, Flask routes for API. React 19 + TypeScript frontend with React Query is modern and appropriate.

---

## Critical Issues

### 1. SQL Injection Pattern
- **File:** `database/repositories/video_repository.py:136`
- Uses `.format()` to inject value into SQL instead of parameterized query
- **Fix:** Use `?` placeholder for the hours parameter

### 2. Hardcoded Default Secret Keys
- **Files:** `config/settings.py:247`, `utils/auth.py:14`
- Default values like `'dev-secret-key-change-in-production'` allow JWT forgery if unchanged
- **Fix:** Fail loudly at startup if default key detected

### 3. SMTP Passwords Stored in Plaintext
- **File:** `database/repositories/email_settings_repository.py:210-216`
- TODO comment acknowledges the gap; passwords stored unencrypted in SQLite
- **Fix:** Implement field-level encryption using `cryptography` library

### 4. Path Traversal in File Upload
- **File:** `services/processing_service.py:54-62`
- Filename from upload used directly in path construction without sanitization
- **Fix:** Validate filename against allowlist pattern; reject `..` sequences

### 5. Path Traversal in Log Download
- **File:** `web/admin_routes.py:63`
- `download_logs_handler(filename)` doesn't validate against directory traversal
- **Fix:** Verify resolved path is within allowed logs directory

### 6. Registration Links Never Expire
- **File:** `database/repositories/registration_repository.py:45-52`
- `get_by_token()` checks `is_active` but never checks `expires_at`
- **Fix:** Add `AND (expires_at IS NULL OR expires_at > datetime('now'))` to query

### 7. Token Refresh Race Condition (Frontend)
- **File:** `web-ui/src/api/client.ts:513-631`
- `piApi` and `processingApi` share single `isRefreshing` flag and `failedQueue`
- Simultaneous 401s cause requests to replay with wrong client's token
- **Fix:** Separate refresh state per API client instance

### 8. Auth Token in URL Parameters
- **File:** `web-ui/src/api/client.ts:190-227`
- JWT token passed as query parameter for camera streams
- Exposed in browser history, server logs, referrer headers
- **Fix:** Use Authorization header or cookie-based auth for streams

### 9. Missing CORS Origin Whitelist
- **File:** `web/app.py:14-15`
- `CORS(app)` allows any origin when enabled
- **Fix:** Configure explicit allowed origins

### 10. Missing CSRF Protection
- No CSRF tokens on any state-changing endpoint
- **Fix:** Implement CSRF protection via Flask-WTF or custom middleware

---

## Medium-Severity Issues

| # | Issue | Location |
|---|-------|----------|
| 11 | No rate limiting on login | `web/routes/auth_routes.py:17-44` |
| 12 | Missing HTTP security headers | `web/app.py` |
| 13 | No React error boundary | App crashes show blank screen |
| 14 | Hardcoded 640x480 resolution | `web-ui/src/components/InteractiveCameraFeed.tsx:106-122` |
| 15 | LogViewer infinite re-render loop | `web-ui/src/components/LogViewer.tsx:84-97` |
| 16 | Token refresh continues after failure | `web-ui/src/contexts/AuthProvider.tsx:110-134` |
| 17 | Missing cleanup on unmount | `web-ui/src/pages/Register.tsx`, `VerifyEmail.tsx` |
| 18 | Processing lock doesn't cover DB updates | `services/processing_service.py:169-205` |
| 19 | TOCTOU race in file deletion | `services/processing_service.py:457-467` |
| 20 | Broad exception catching masks errors | Multiple route handlers |
| 21 | Dead code: `accessDenied` never updated | `web-ui/src/pages/AdminPanel.tsx:24` |
| 22 | Unsafe type cast via `unknown` | `web-ui/src/components/InteractiveCameraFeed.tsx:228` |
| 23 | Open redirect via `location.state` | `web-ui/src/pages/Login.tsx:17` |
| 24 | No `gcTime` on React Query client | `web-ui/src/App.tsx:18-26` |

---

## Test Coverage

**Estimated: <30%**

### Completely Untested
- Email service (SMTP, Azure AD)
- Video processing pipeline
- Multi-camera coordination
- Database concurrent access
- Video retention/cleanup

### Broken or Placeholder Tests
- `tests/api/test_security_audit.py:42` — `requires_auth()` always returns `True`
- `web-ui/src/contexts/AuthContext.test.tsx:101` — token refresh test skipped
- `tests/api/test_endpoint_details.py:36` — accepts status 200-500 as passing
- `.pre-commit-config.yaml:31` — references nonexistent `tests/unit/` directory

---

## Configuration & Deployment

| Issue | Location |
|-------|----------|
| Hardcoded `User=craig` | `systemd/ai-processor.service:7` |
| Default password `changeme` | `.env.docker.example:7` |
| No resource limits in systemd | Both service files |
| `PrivateDevices=no` exposes all devices | `systemd/pi-capture.service:26` |
| Unquoted variables in install scripts | `scripts/setup/install_ai_processor_service.sh:92` |
| bcrypt pinned to 3.x (missing updates) | `requirements.processor.txt:23` |
| IPython in production requirements | `requirements.processor.txt:39` |
| No hash verification in requirements | Both requirements files |

---

## Priority Remediation Plan

### Immediate (Security)
1. Parameterize SQL in video_repository.py
2. Require non-default SECRET_KEY at startup
3. Sanitize filenames in upload and log download
4. Add expiration check to registration links
5. Separate token refresh state per API client
6. Remove auth token from URL query parameters

### Short-term (Hardening)
7. Encrypt SMTP passwords in database
8. Add CORS origin whitelist
9. Add CSRF protection
10. Add rate limiting on auth endpoints
11. Add React error boundary
12. Fix LogViewer re-render loop

### Medium-term (Quality)
13. Increase test coverage (email, video, concurrent DB)
14. Fix broken pre-commit config
15. Remove hardcoded usernames from systemd/scripts
16. Add resource limits to systemd services
17. Move IPython to dev-only requirements
