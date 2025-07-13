#!/usr/bin/env python3
"""
Test suite for web routes timeout and validation fixes
"""
import pytest
import json
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flask import Flask
from core.models import MotionRegion


class TestWebRoutesTimeoutFixes:
    """Test web routes timeout fixes"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        
        # Mock sync service
        self.mock_sync_service = Mock()
        self.mock_sync_service.base_url = 'http://test-server:8091'
    
    @patch('requests.get')
    def test_serve_video_has_timeout(self, mock_get):
        """Test that serve_video requests have timeout"""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'video/mp4'}
        mock_response.iter_content.return_value = [b'video data']
        mock_get.return_value = mock_response
        
        # Import and setup route (this would normally be done by the app factory)
        from web.routes.capture_routes import create_capture_routes
        
        # Create minimal app context
        with self.app.test_request_context():
            # Mock the required services
            capture_services = {0: Mock()}
            settings_repos = {0: Mock()}
            
            # Create routes
            create_capture_routes(self.app, capture_services, self.mock_sync_service, settings_repos)
            
            with self.app.test_client() as client:
                # Mock get_service function to return our mock
                with patch('web.routes.capture_routes.get_service', return_value=Mock()):
                    response = client.get('/videos/test.mp4')
                
                # Verify that requests.get was called with timeout
                mock_get.assert_called_once()
                call_args = mock_get.call_args
                assert 'timeout' in call_args[1]
                assert call_args[1]['timeout'] == 30
    
    @patch('requests.get')
    def test_serve_thumbnail_has_timeout(self, mock_get):
        """Test that serve_thumbnail requests have timeout"""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'image/jpeg'}
        mock_response.iter_content.return_value = [b'image data']
        mock_get.return_value = mock_response
        
        # Import and setup route
        from web.routes.capture_routes import create_capture_routes
        
        # Create minimal app context
        with self.app.test_request_context():
            # Mock the required services
            capture_services = {0: Mock()}
            settings_repos = {0: Mock()}
            
            # Create routes
            create_capture_routes(self.app, capture_services, self.mock_sync_service, settings_repos)
            
            with self.app.test_client() as client:
                # Mock get_service function to return our mock
                with patch('web.routes.capture_routes.get_service', return_value=Mock()):
                    response = client.get('/thumbnails/test.jpg')
                
                # Verify that requests.get was called with timeout
                mock_get.assert_called_once()
                call_args = mock_get.call_args
                assert 'timeout' in call_args[1]
                assert call_args[1]['timeout'] == 10


class TestMotionSettingsValidation:
    """Test motion settings validation fixes"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        
        # Mock services
        self.mock_capture_service = Mock()
        self.mock_sync_service = Mock()
        self.mock_settings_repo = Mock()
    
    def test_motion_settings_coordinate_validation(self):
        """Test that motion settings validate coordinates properly"""
        from web.routes.capture_routes import create_capture_routes
        
        # Create minimal app context
        with self.app.test_request_context():
            # Mock the required services
            capture_services = {0: self.mock_capture_service}
            settings_repos = {0: self.mock_settings_repo}
            
            # Create routes
            create_capture_routes(self.app, capture_services, self.mock_sync_service, settings_repos)
            
            with self.app.test_client() as client:
                # Mock get_service function
                with patch('web.routes.capture_routes.get_service', return_value=self.mock_capture_service):
                    # Test invalid coordinates (x1 >= x2)
                    invalid_data = {
                        'region': {'x1': 100, 'y1': 50, 'x2': 50, 'y2': 100},
                        'motion_threshold': 5000,
                        'min_contour_area': 500,
                        'motion_timeout_seconds': 30
                    }
                    
                    response = client.post('/api/motion-settings', 
                                         data=json.dumps(invalid_data),
                                         content_type='application/json')
                    
                    assert response.status_code == 400
                    assert b'Invalid region dimensions' in response.data
    
    def test_motion_settings_negative_coordinates(self):
        """Test that negative coordinates are rejected"""
        from web.routes.capture_routes import create_capture_routes
        
        with self.app.test_request_context():
            capture_services = {0: self.mock_capture_service}
            settings_repos = {0: self.mock_settings_repo}
            
            create_capture_routes(self.app, capture_services, self.mock_sync_service, settings_repos)
            
            with self.app.test_client() as client:
                with patch('web.routes.capture_routes.get_service', return_value=self.mock_capture_service):
                    # Test negative coordinates
                    invalid_data = {
                        'region': {'x1': -10, 'y1': 50, 'x2': 100, 'y2': 200},
                        'motion_threshold': 5000,
                        'min_contour_area': 500,
                        'motion_timeout_seconds': 30
                    }
                    
                    response = client.post('/api/motion-settings', 
                                         data=json.dumps(invalid_data),
                                         content_type='application/json')
                    
                    assert response.status_code == 400
                    assert b'Coordinates must be non-negative' in response.data
    
    def test_motion_settings_invalid_threshold(self):
        """Test that invalid motion threshold is rejected"""
        from web.routes.capture_routes import create_capture_routes
        
        with self.app.test_request_context():
            capture_services = {0: self.mock_capture_service}
            settings_repos = {0: self.mock_settings_repo}
            
            create_capture_routes(self.app, capture_services, self.mock_sync_service, settings_repos)
            
            with self.app.test_client() as client:
                with patch('web.routes.capture_routes.get_service', return_value=self.mock_capture_service):
                    # Test invalid motion threshold
                    invalid_data = {
                        'region': {'x1': 10, 'y1': 50, 'x2': 100, 'y2': 200},
                        'motion_threshold': -100,  # Invalid negative threshold
                        'min_contour_area': 500,
                        'motion_timeout_seconds': 30
                    }
                    
                    response = client.post('/api/motion-settings', 
                                         data=json.dumps(invalid_data),
                                         content_type='application/json')
                    
                    assert response.status_code == 400
                    assert b'Motion threshold must be positive' in response.data
    
    def test_motion_settings_valid_data(self):
        """Test that valid motion settings are accepted"""
        from web.routes.capture_routes import create_capture_routes
        
        with self.app.test_request_context():
            capture_services = {0: self.mock_capture_service}
            settings_repos = {0: self.mock_settings_repo}
            
            create_capture_routes(self.app, capture_services, self.mock_sync_service, settings_repos)
            
            with self.app.test_client() as client:
                with patch('web.routes.capture_routes.get_service', return_value=self.mock_capture_service):
                    # Test valid data
                    valid_data = {
                        'region': {'x1': 10, 'y1': 50, 'x2': 100, 'y2': 200},
                        'motion_threshold': 5000,
                        'min_contour_area': 500,
                        'motion_timeout_seconds': 30
                    }
                    
                    response = client.post('/api/motion-settings', 
                                         data=json.dumps(valid_data),
                                         content_type='application/json')
                    
                    # Should succeed (200 or 201)
                    assert response.status_code in [200, 201]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])