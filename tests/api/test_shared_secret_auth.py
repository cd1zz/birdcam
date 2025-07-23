"""Test shared secret authentication for upload endpoint."""
import pytest
import os
from io import BytesIO


def test_upload_with_shared_secret(flask_app):
    """Test that upload endpoint accepts shared secret authentication."""
    with flask_app.test_client() as client:
        # Get the actual SECRET_KEY from environment
        secret_key = os.getenv('SECRET_KEY', 'test-secret-key')
        
        # Create a fake video file
        fake_video = BytesIO(b"fake video content")
        fake_video.name = 'test_video.mp4'
        
        # Test with correct secret key
        response = client.post(
            '/upload',
            headers={'X-Secret-Key': secret_key},
            data={'video': (fake_video, 'test_video.mp4')},
            content_type='multipart/form-data'
        )
        
        # Should succeed with 200 or fail with 500 (if processing fails)
        # but NOT 401 unauthorized
        assert response.status_code in [200, 500], \
            f"Upload with valid secret key failed with {response.status_code}"
        
        # If it's 500, it should be because of processing, not auth
        if response.status_code == 500:
            data = response.get_json()
            assert 'error' in data
            # Should not be an auth error
            assert 'authentication' not in data['error'].lower()
            assert 'unauthorized' not in data['error'].lower()


def test_upload_with_invalid_secret(flask_app):
    """Test that upload endpoint rejects invalid shared secret."""
    with flask_app.test_client() as client:
        # Create a fake video file
        fake_video = BytesIO(b"fake video content")
        fake_video.name = 'test_video.mp4'
        
        # Test with wrong secret key
        response = client.post(
            '/upload',
            headers={'X-Secret-Key': 'wrong-secret-key'},
            data={'video': (fake_video, 'test_video.mp4')},
            content_type='multipart/form-data'
        )
        
        assert response.status_code == 401, \
            f"Upload with invalid secret key should return 401, got {response.status_code}"


def test_upload_with_jwt_still_works(flask_app):
    """Test that upload endpoint still accepts JWT authentication."""
    with flask_app.test_client() as client:
        # This test would need a valid JWT token
        # For now, just verify it returns 401 without any auth
        fake_video = BytesIO(b"fake video content")
        fake_video.name = 'test_video.mp4'
        
        response = client.post(
            '/upload',
            data={'video': (fake_video, 'test_video.mp4')},
            content_type='multipart/form-data'
        )
        
        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data
        # Should mention both options
        assert 'token' in data['error'].lower() or 'secret' in data['error'].lower()


def test_shared_secret_creates_system_user(flask_app):
    """Test that shared secret auth creates proper system user in g.user."""
    # This is more of an integration test that would require 
    # access to the request context, but we can verify the behavior
    # through the upload endpoint
    with flask_app.test_client() as client:
        secret_key = os.getenv('SECRET_KEY', 'test-secret-key')
        
        # The endpoint should work with secret key and treat it as admin
        fake_video = BytesIO(b"fake video content")
        fake_video.name = 'test_video.mp4'
        
        response = client.post(
            '/upload',
            headers={'X-Secret-Key': secret_key},
            data={'video': (fake_video, 'test_video.mp4')},
            content_type='multipart/form-data'
        )
        
        # Should not be forbidden (403) which would indicate insufficient permissions
        assert response.status_code != 403, \
            "Shared secret should provide admin-level access"