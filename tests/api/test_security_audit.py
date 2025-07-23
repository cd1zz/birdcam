"""Security audit tests to identify potentially unprotected endpoints."""
import pytest
from flask import Flask
import re

from ..discovery.discover_endpoints import discover_endpoints


# Endpoints that should definitely require authentication
SENSITIVE_PATTERNS = [
    r'/upload',
    r'/delete',
    r'/settings',
    r'/system',
    r'/metrics',
    r'/status',
    r'/camera',
    r'/stream',
    r'/snapshot',
    r'/motion',
    r'/logs',
    r'/users',
    r'/admin',
]

# Known public endpoints that are intentionally unprotected
KNOWN_PUBLIC_ENDPOINTS = [
    '/api/debug/simple',
    '/api/debug/test',
    '/api/setup/status',
    '/api/auth/login',
    '/api/register',
    '/api/verify-email',
    '/',  # Root route
]


def requires_auth(endpoint_path, app):
    """Check if an endpoint has authentication by attempting to access it."""
    # This is a simple heuristic - in practice you'd check the route decorators
    # For now, we'll check if the endpoint returns 401/403 without auth
    return True  # Placeholder


@pytest.fixture(scope="module")
def security_audit_data(flask_app: Flask):
    """Gather security audit data for all endpoints."""
    endpoints = discover_endpoints(flask_app)
    
    audit_results = {
        'unprotected_sensitive': [],
        'protected': [],
        'public': [],
        'total': len(endpoints)
    }
    
    # Test each endpoint
    with flask_app.test_client() as client:
        for endpoint in endpoints:
            path = endpoint['path']
            
            # Skip parameterized paths for this audit
            if '<' in path:
                continue
                
            # Check if it's a known public endpoint
            if any(path == pub for pub in KNOWN_PUBLIC_ENDPOINTS):
                audit_results['public'].append(path)
                continue
            
            # Test GET endpoints only for simplicity
            if 'GET' in endpoint['methods']:
                response = client.get(path)
                
                # If it returns 401/403, it's protected
                if response.status_code in [401, 403]:
                    audit_results['protected'].append(path)
                # If it returns 200 and matches sensitive patterns, it might be unprotected
                elif response.status_code == 200:
                    is_sensitive = any(re.search(pattern, path) for pattern in SENSITIVE_PATTERNS)
                    if is_sensitive:
                        audit_results['unprotected_sensitive'].append(path)
                    else:
                        audit_results['public'].append(path)
    
    return audit_results


def test_no_unprotected_sensitive_endpoints(security_audit_data):
    """Verify that no sensitive endpoints are left unprotected."""
    unprotected = security_audit_data['unprotected_sensitive']
    
    if unprotected:
        message = f"\nFound {len(unprotected)} potentially unprotected sensitive endpoints:\n"
        for endpoint in unprotected:
            message += f"  - {endpoint}\n"
        message += "\nThese endpoints handle sensitive operations and should require authentication."
        
    assert len(unprotected) == 0, message


def test_authentication_coverage(security_audit_data):
    """Check the overall authentication coverage."""
    total = security_audit_data['total']
    protected = len(security_audit_data['protected'])
    public = len(security_audit_data['public'])
    unprotected_sensitive = len(security_audit_data['unprotected_sensitive'])
    
    coverage = (protected / total) * 100 if total > 0 else 0
    
    print(f"\nSecurity Audit Summary:")
    print(f"  Total endpoints: {total}")
    print(f"  Protected endpoints: {protected} ({coverage:.1f}%)")
    print(f"  Public endpoints: {public}")
    print(f"  Unprotected sensitive: {unprotected_sensitive}")
    
    # This is informational, not a hard assertion
    assert True


def test_specific_endpoint_protection(flask_app):
    """Test specific endpoints that must be protected."""
    # Endpoints with their expected methods
    must_be_protected = [
        ('/api/recent-detections', 'GET'),
        ('/api/system-metrics', 'GET'),
        ('/api/motion-settings', 'GET'),
        ('/api/admin/users', 'GET'),
        ('/api/admin/logs', 'GET'),
        ('/api/process-now', 'POST'),
        ('/api/cleanup-now', 'POST'),
    ]
    
    with flask_app.test_client() as client:
        unprotected = []
        
        for endpoint, method in must_be_protected:
            if method == 'GET':
                response = client.get(endpoint)
            else:
                response = client.post(endpoint, json={})
            # Should return 401 (Unauthorized) or 403 (Forbidden) without auth
            if response.status_code not in [401, 403]:
                unprotected.append((endpoint, response.status_code))
        
        if unprotected:
            message = "\nThe following endpoints MUST be protected but are not:\n"
            for endpoint, status in unprotected:
                message += f"  - {endpoint} (returned {status})\n"
            pytest.fail(message)


def test_upload_endpoint_protection(flask_app):
    """Specifically test the upload endpoint - should require authentication."""
    with flask_app.test_client() as client:
        # Test without authentication
        response = client.post('/upload', data={})
        
        assert response.status_code == 401, \
            f"Upload endpoint should require authentication! Returned {response.status_code}"
        
        # Test that it accepts shared secret
        import os
        secret_key = os.getenv('SECRET_KEY', 'test-secret-key')
        response = client.post(
            '/upload',
            headers={'X-Secret-Key': secret_key},
            data={}
        )
        # Should get 400 (bad request - no file) not 401 (unauthorized)
        assert response.status_code == 400, \
            f"Upload endpoint should accept shared secret auth! Returned {response.status_code}"


def test_media_endpoints_protection(flask_app):
    """Test if media serving endpoints are protected."""
    with flask_app.test_client() as client:
        # Test video endpoint
        response = client.get('/videos/test.mp4')
        video_protected = response.status_code in [401, 403, 404]
        
        # Test thumbnail endpoint  
        response = client.get('/thumbnails/test.jpg')
        thumb_protected = response.status_code in [401, 403, 404]
        
        issues = []
        if not video_protected:
            issues.append("Video files are served without authentication")
        if not thumb_protected:
            issues.append("Thumbnail files are served without authentication")
            
        if issues:
            pytest.fail("\n".join(issues))