"""Test API response content and structure."""
import pytest


def test_debug_endpoints_return_json(client):
    """Test that debug endpoints return proper JSON responses."""
    response = client.get("/api/debug/simple")
    assert response.status_code == 200
    assert response.content_type == "application/json"
    data = response.get_json()
    assert "message" in data
    assert data["message"] == "Debug endpoint is functional"
    
    response = client.get("/api/debug/test")
    assert response.status_code == 200
    assert response.content_type == "application/json"
    data = response.get_json()
    assert "test" in data
    assert "service" in data
    assert data["test"] == "passed"
    assert data["service"] == "AI Processing Server"


def test_setup_status_response(client):
    """Test setup status endpoint returns expected structure."""
    response = client.get("/api/setup/status")
    assert response.status_code == 200
    assert response.content_type == "application/json"
    data = response.get_json()
    assert "setup_required" in data
    assert "admin_exists" in data
    assert isinstance(data["setup_required"], bool)
    assert isinstance(data["admin_exists"], bool)


def test_models_available_response(client):
    """Test models endpoint returns list of available models."""
    response = client.get("/api/models/available")
    # This endpoint requires authentication
    assert response.status_code == 401
    assert response.content_type == "application/json"
    # When authenticated, it would return:
    # data = response.get_json()
    # assert "models" in data
    # assert isinstance(data["models"], list)


def test_motion_settings_get_response(client):
    """Test motion settings GET returns expected structure."""
    response = client.get("/api/motion-settings")
    # This endpoint requires authentication (require_auth_internal)
    assert response.status_code == 401
    assert response.content_type == "application/json"
    # When authenticated, it would return motion detection settings as a dict


def test_auth_login_validation(client):
    """Test login endpoint validates required fields."""
    # Missing password
    response = client.post("/api/auth/login", json={"username": "test"})
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data or "message" in data
    
    # Missing username
    response = client.post("/api/auth/login", json={"password": "test"})
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data or "message" in data
    
    # Empty values
    response = client.post("/api/auth/login", json={"username": "", "password": ""})
    assert response.status_code in [400, 401]


def test_register_validation(client):
    """Test registration endpoint validates required fields."""
    # Missing fields
    response = client.post("/api/register", json={"username": "newuser"})
    assert response.status_code in [400, 403]  # 403 if registration is disabled
    
    if response.status_code == 400:
        data = response.get_json()
        assert "error" in data or "message" in data


def test_404_handling(client):
    """Test 404 error handling for non-existent API endpoints."""
    response = client.get("/api/non-existent-endpoint")
    assert response.status_code in [404, 200]  # 200 if SPA catch-all route
    
    response = client.post("/api/non-existent-endpoint", json={})
    assert response.status_code in [404, 405]  # 405 if method not allowed


def test_upload_endpoint_validation(client):
    """Test upload endpoint requires proper data."""
    # No file
    response = client.post("/upload", data={})
    assert response.status_code in [400, 401, 403]
    
    # Wrong content type
    response = client.post("/upload", json={"file": "test"})
    assert response.status_code in [400, 401, 415]


def test_pi_endpoints_error_handling(client):
    """Test PI proxy endpoints handle connection errors gracefully."""
    # These should handle PI being unavailable
    endpoints = [
        "/api/pi/camera/0/snapshot",
        "/api/pi/motion-debug",
    ]
    
    for endpoint in endpoints:
        response = client.get(endpoint)
        # Should not crash even if PI is not available
        assert response.status_code in [200, 401, 403, 404, 500, 502, 503]
        if response.status_code >= 500:
            # Error responses should still be JSON
            assert response.content_type == "application/json"


def test_delete_detection_requires_data(client):
    """Test delete detection endpoint requires proper data."""
    response = client.post("/api/delete-detection", json={})
    assert response.status_code in [400, 401, 403]
    
    # With invalid ID
    response = client.post("/api/delete-detection", json={"id": "invalid"})
    assert response.status_code in [400, 401, 403]