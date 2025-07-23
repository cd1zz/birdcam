"""Test admin API routes organization and functionality"""

import pytest
from unittest.mock import patch, MagicMock, Mock
from flask import Flask, g
from web.app import create_processing_app
from core.models import VideoFile, ProcessingStatus, BirdDetection, User, UserRole
from datetime import datetime, timezone
import jwt
import os
import tempfile
from pathlib import Path


class TestAdminAPIRoutes:
    """Test the new /api/admin/* route structure"""
    
    @pytest.fixture
    def app(self):
        """Create test Flask app"""
        # Create mock dependencies
        processing_service = Mock()
        processing_service.model_manager = Mock()
        processing_service.model_manager.is_loaded = True
        
        video_repo = Mock()
        detection_repo = Mock()
        
        # Create test config
        test_config = Mock()
        test_config.database = Mock()
        test_config.database.path = ':memory:'
        test_config.processing = Mock()
        test_config.processing.storage_path = Path('/tmp')
        test_config.processing.detection = Mock()
        test_config.processing.detection.classes = ['bird', 'cat', 'dog']
        test_config.processing.detection.confidences = {'bird': 0.5, 'cat': 0.6, 'dog': 0.7, 'default': 0.5}
        test_config.processing.storage_days = Mock()
        test_config.processing.storage_days.detections = 30
        test_config.processing.storage_days.no_detections = 7
        test_config.sync = Mock()
        test_config.sync.interval_minutes = 15
        test_config.sync.batch_size = 10
        test_config.security = Mock()
        test_config.security.secret_key = 'test-secret-key'
        
        app = create_processing_app(processing_service, video_repo, detection_repo, test_config)
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        app.config['DATABASE_PATH'] = ':memory:'
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()
    
    @pytest.fixture  
    def admin_user(self):
        """Create mock admin user"""
        user = Mock(spec=User)
        user.id = 1
        user.username = 'admin'
        user.role = UserRole.ADMIN
        user.email = 'admin@test.com'
        user.is_active = True
        user.created_at = Mock()
        user.created_at.isoformat.return_value = '2024-01-01T00:00:00'
        user.last_login = None  # Can be None according to the handler
        return user
    
    @pytest.fixture
    def viewer_user(self):
        """Create mock viewer user"""
        user = Mock(spec=User)
        user.id = 2
        user.username = 'viewer'
        user.role = UserRole.VIEWER
        user.email = 'viewer@test.com'
        user.is_active = True
        user.created_at = Mock()
        user.created_at.isoformat.return_value = '2024-01-01T00:00:00'
        user.last_login = None  # Can be None according to the handler
        return user
    
    @pytest.fixture
    def mock_auth_service(self, admin_user, viewer_user):
        """Mock auth service"""
        with patch('web.middleware.auth.get_auth_service') as mock_get_auth:
            auth_service = Mock()
            mock_get_auth.return_value = auth_service
            
            # Setup token validation
            def validate_token(token):
                if token == 'admin-token':
                    return admin_user
                elif token == 'viewer-token':
                    return viewer_user
                return None
            
            auth_service.validate_token = validate_token
            yield auth_service
    
    @pytest.fixture
    def mock_user_repo(self, admin_user, viewer_user):
        """Mock user repository"""
        with patch('web.handlers.auth_handlers.get_auth_service') as mock_get_auth:
            auth_service = Mock()
            mock_get_auth.return_value = auth_service
            
            # Mock the user_repository
            user_repo = Mock()
            auth_service.user_repository = user_repo
            
            # Mock get_all method
            user_repo.get_all.return_value = [admin_user, viewer_user]
            
            # Mock get_by_id method
            def get_by_id(user_id):
                if user_id == 1:
                    return admin_user
                elif user_id == 2:
                    return viewer_user
                return None
            
            user_repo.get_by_id = get_by_id
            
            yield user_repo
    
    def test_admin_users_routes(self, client, mock_auth_service, mock_user_repo):
        """Test user management routes moved to /api/admin/users"""
        # Test GET /api/admin/users
        response = client.get('/api/admin/users', 
                            headers={'Authorization': 'Bearer admin-token'})
        assert response.status_code == 200
        data = response.get_json()
        assert 'users' in data
        assert len(data['users']) == 2
        assert data['users'][0]['username'] == 'admin'
        
        # Test old route should not exist
        response = client.get('/api/auth/users', 
                            headers={'Authorization': 'Bearer admin-token'})
        assert response.status_code == 404
    
    def test_admin_logs_routes(self, client, mock_auth_service):
        """Test log management routes under /api/admin/logs"""
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', MagicMock()):
                # Test GET /api/admin/logs
                response = client.get('/api/admin/logs',
                                    headers={'Authorization': 'Bearer admin-token'})
                assert response.status_code == 200
    
    def test_admin_settings_routes(self, client, mock_auth_service):
        """Test system settings routes under /api/admin/settings"""
        # Test GET /api/admin/settings/system
        response = client.get('/api/admin/settings/system',
                            headers={'Authorization': 'Bearer admin-token'})
        assert response.status_code == 200
        data = response.get_json()
        assert 'detection' in data
        assert 'storage' in data
        assert 'sync' in data
    
    def test_admin_stats_routes(self, client, mock_auth_service):
        """Test system stats routes under /api/admin/stats"""
        with patch('psutil.cpu_percent', return_value=25.0):
            with patch('psutil.virtual_memory') as mock_mem:
                mock_mem.return_value.percent = 50.0
                mock_mem.return_value.used = 4 * 1024**3
                mock_mem.return_value.total = 8 * 1024**3
                
                with patch('psutil.disk_usage') as mock_disk:
                    mock_disk.return_value.percent = 60.0
                    mock_disk.return_value.used = 60 * 1024**3
                    mock_disk.return_value.total = 100 * 1024**3
                    mock_disk.return_value.free = 40 * 1024**3
                    
                    response = client.get('/api/admin/stats/system',
                                        headers={'Authorization': 'Bearer admin-token'})
                    assert response.status_code == 200
                    data = response.get_json()
                    assert data['cpu_percent'] == 25.0
                    assert data['memory']['percent'] == 50.0
                    assert data['disk']['percent'] == 60.0
    
    def test_viewer_cannot_access_admin_routes(self, client, mock_auth_service, mock_user_repo):
        """Test that viewers cannot access admin-only routes"""
        # Test user management
        response = client.get('/api/admin/users',
                            headers={'Authorization': 'Bearer viewer-token'})
        assert response.status_code == 403
        
        # Test system settings update
        response = client.post('/api/admin/settings/system',
                            json={'detection': {'confidence_threshold': 0.8}},
                            headers={'Authorization': 'Bearer viewer-token'})
        assert response.status_code == 403
    
    def test_registration_routes_remain_under_admin(self, client, mock_auth_service, app):
        """Test that registration routes remain under /api/admin/registration"""
        # Simply check that the routes exist in the URL map
        route_paths = [rule.rule for rule in app.url_map.iter_rules()]
        
        # Verify registration routes exist under /api/admin/registration
        assert '/api/admin/registration/links' in route_paths
        assert '/api/admin/registration/links/<int:link_id>' in route_paths
        # Check that we have some registration routes under admin (actual paths may vary)
        registration_routes = [r for r in route_paths if '/api/admin/registration' in r]
        assert len(registration_routes) >= 2  # At least links and links/<id>
    
    def test_no_duplicate_routes(self, app):
        """Test that there are no duplicate route registrations"""
        routes = []
        for rule in app.url_map.iter_rules():
            if rule.endpoint != 'static':
                routes.append((rule.rule, sorted(rule.methods - {'HEAD', 'OPTIONS'})))
        
        # Check for duplicates
        route_count = {}
        for route, methods in routes:
            key = f"{route} {methods}"
            route_count[key] = route_count.get(key, 0) + 1
        
        duplicates = {k: v for k, v in route_count.items() if v > 1}
        assert len(duplicates) == 0, f"Found duplicate routes: {duplicates}"
        
        # Verify key admin routes exist
        route_paths = [rule.rule for rule in app.url_map.iter_rules()]
        assert '/api/admin/users' in route_paths
        assert '/api/admin/users/<int:user_id>' in route_paths
        assert '/api/admin/settings/system' in route_paths
        assert '/api/admin/stats/system' in route_paths
        
        # Verify old user routes don't exist
        assert '/api/auth/users' not in route_paths
        assert '/api/auth/users/<int:user_id>' not in route_paths