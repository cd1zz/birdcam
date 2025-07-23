"""Detailed endpoint testing to verify API behavior."""
import pytest
from flask import Flask


def test_public_endpoints_no_auth(client):
    """Test that public endpoints work without authentication."""
    public_endpoints = [
        ("/api/setup/status", 200),
        ("/api/debug/simple", 200),
        ("/api/debug/test", 200),
    ]
    
    for endpoint, expected_status in public_endpoints:
        response = client.get(endpoint)
        assert response.status_code == expected_status, f"Failed for {endpoint}"


def test_auth_endpoints_require_login(client):
    """Test that protected endpoints require authentication."""
    protected_endpoints = [
        "/api/status",
        "/api/recent-detections",
        "/api/system-metrics",
        "/api/auth/me",
        "/api/admin/users",
        "/api/admin/logs",
    ]
    
    for endpoint in protected_endpoints:
        response = client.get(endpoint)
        # Should return 401 Unauthorized or 403 Forbidden without auth
        assert response.status_code in [401, 403], f"Endpoint {endpoint} not protected"


def test_post_endpoints_with_invalid_data(client):
    """Test POST endpoints with invalid/missing data."""
    post_endpoints = [
        "/api/auth/login",
        "/api/register",
        "/api/verify-email",
    ]
    
    for endpoint in post_endpoints:
        # Send empty JSON
        response = client.post(endpoint, json={})
        # Should return 400 Bad Request for missing required fields
        assert response.status_code in [400, 401, 403], f"Endpoint {endpoint} accepted empty data"


def test_video_endpoints_with_nonexistent_files(client):
    """Test video/thumbnail endpoints with non-existent files."""
    response = client.get("/videos/nonexistent.mp4")
    assert response.status_code == 404
    
    response = client.get("/thumbnails/nonexistent.jpg")
    assert response.status_code == 404


def test_admin_endpoints_require_admin_role(client):
    """Test that admin endpoints are properly protected."""
    admin_endpoints = [
        "/api/admin/users",
        "/api/admin/settings/system",
        "/api/admin/stats/system",
        "/api/admin/email/templates",
    ]
    
    for endpoint in admin_endpoints:
        response = client.get(endpoint)
        # Should require authentication
        assert response.status_code in [401, 403], f"Admin endpoint {endpoint} not properly protected"


def test_pi_proxy_endpoints(client):
    """Test PI camera proxy endpoints."""
    pi_endpoints = [
        "/api/pi/status",
        "/api/pi/cameras",
        "/api/pi/system-metrics",
    ]
    
    for endpoint in pi_endpoints:
        response = client.get(endpoint)
        # These might fail if PI is not configured, but should not crash
        assert response.status_code in [200, 401, 403, 404, 500, 502, 503], f"Unexpected status for {endpoint}"


def test_motion_settings_endpoints(client):
    """Test motion settings GET/POST endpoints."""
    # GET should work (returns defaults or current settings)
    response = client.get("/api/motion-settings")
    assert response.status_code in [200, 401, 403]
    
    # POST with invalid data should fail gracefully
    response = client.post("/api/motion-settings", json={})
    assert response.status_code in [400, 401, 403]


def test_model_endpoints(client):
    """Test AI model related endpoints."""
    # Available models
    response = client.get("/api/models/available")
    assert response.status_code in [200, 401, 403]
    
    # Model classes (with test model ID)
    response = client.get("/api/models/yolov5s/classes")
    assert response.status_code in [200, 401, 403, 404]


def test_registration_flow_endpoints(client):
    """Test registration and email verification endpoints."""
    # Registration with invalid data
    response = client.post("/api/register", json={"username": "test"})
    assert response.status_code in [400, 403]  # Missing required fields or registration disabled
    
    # Email verification with invalid token
    response = client.post("/api/verify-email", json={"token": "invalid"})
    assert response.status_code in [400, 401]
    
    # Resend verification without being logged in
    response = client.post("/api/resend-verification", json={})
    assert response.status_code in [400, 401, 403]


def test_static_file_serving(client):
    """Test static file serving endpoints."""
    # Root should serve index.html or redirect
    response = client.get("/")
    assert response.status_code in [200, 302]
    
    # Non-existent path should return 404 or serve index.html (for SPA)
    response = client.get("/nonexistent-page")
    assert response.status_code in [200, 404]


def test_error_handling_for_malformed_requests(client):
    """Test that endpoints handle malformed requests gracefully."""
    # Send non-JSON to JSON endpoint
    response = client.post(
        "/api/auth/login",
        data="not json",
        content_type="application/json"
    )
    assert response.status_code in [400, 415]  # Bad Request or Unsupported Media Type
    
    # Send wrong content type
    response = client.post(
        "/api/auth/login",
        data="username=test&password=test",
        content_type="application/x-www-form-urlencoded"
    )
    assert response.status_code in [400, 415]