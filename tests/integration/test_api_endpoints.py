#!/usr/bin/env python3
"""
Integration tests for API endpoints
Tests the complete API functionality and error handling
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from web.app import create_processing_app
from database.connection import DatabaseManager
from database.repositories.video_repository import VideoRepository
from database.repositories.detection_repository import DetectionRepository
from services.processing_service import ProcessingService
from core.models import VideoFile, BirdDetection
from config.settings import ProcessingConfig, DetectionConfig


class TestAPIEndpoints:
    """Test API endpoints and error scenarios"""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir)
            
            # Create required subdirectories
            (storage_path / "incoming").mkdir()
            (storage_path / "processed" / "detections").mkdir(parents=True)
            (storage_path / "processed" / "no_detections").mkdir(parents=True)
            (storage_path / "thumbnails").mkdir()
            
            yield storage_path
    
    @pytest.fixture
    def test_config(self, temp_storage):
        """Create test configuration"""
        config = Mock()
        config.database.path = temp_storage / "test.db"
        config.processing.storage_path = temp_storage
        config.processing.detection = DetectionConfig(
            classes=['bird', 'cat', 'dog'],
            confidences={'bird': 0.5, 'cat': 0.6, 'dog': 0.7, 'default': 0.5},
            model_name='yolov5n',
            process_every_nth_frame=3,
            max_thumbnails_per_video=5
        )
        config.web.processing_port = 8091
        config.web.host = '0.0.0.0'
        return config
    
    @pytest.fixture 
    def test_app(self, test_config, temp_storage):
        """Create test Flask app with test database"""
        # Setup database
        db_manager = DatabaseManager(str(test_config.database.path))
        video_repo = VideoRepository(db_manager)
        detection_repo = DetectionRepository(db_manager)
        
        # Create tables
        video_repo.create_table()
        detection_repo.create_table()
        
        # Create mock processing service
        processing_service = Mock()
        processing_service.model_manager = Mock()
        processing_service.model_manager.is_loaded = True
        
        # Create test data
        self._create_test_data(video_repo, detection_repo)
        
        # Create app
        app = create_processing_app(processing_service, video_repo, detection_repo, test_config)
        app.config['TESTING'] = True
        
        return app, video_repo, detection_repo
    
    def _create_test_data(self, video_repo, detection_repo):
        """Create test data for API testing"""
        base_time = datetime.now()
        
        # Create test videos and detections
        test_cases = [
            {"hours_ago": 1, "species": "bird", "confidence": 0.8, "has_detection": True},
            {"hours_ago": 2, "species": "cat", "confidence": 0.9, "has_detection": True},
            {"hours_ago": 4, "species": "bird", "confidence": 0.7, "has_detection": True},
            {"hours_ago": 6, "species": None, "confidence": 0, "has_detection": False},
            {"hours_ago": 25, "species": "dog", "confidence": 0.85, "has_detection": True},  # Old
        ]
        
        for i, case in enumerate(test_cases):
            # Create video
            video = VideoFile(
                filename=f"test_video_{i}_cam0.mp4",
                original_filename=f"segment_{i}.mp4",
                file_size=1024000,
                duration=30.0,
                fps=10.0,
                resolution="640x480",
                received_time=base_time - timedelta(hours=case["hours_ago"]),
                status="completed"
            )
            video_id = video_repo.create(video)
            
            # Create detection if specified
            if case["has_detection"]:
                detection = BirdDetection(
                    video_id=video_id,
                    frame_number=100,
                    timestamp=5.0,
                    confidence=case["confidence"],
                    bbox=(100, 100, 200, 200),
                    species=case["species"],
                    thumbnail_path=f"thumb_{i}.jpg"
                )
                detection_repo.create(detection)
    
    def test_recent_detections_endpoint_success(self, test_app):
        """Test successful /api/recent-detections requests"""
        app, video_repo, detection_repo = test_app
        
        with app.test_client() as client:
            # Test 1: Basic request
            response = client.get('/api/recent-detections')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert 'detections' in data
            assert len(data['detections']) > 0
            
            # Test 2: With species filter
            response = client.get('/api/recent-detections?species=bird')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            bird_detections = data['detections']
            assert all(d['species'] == 'bird' for d in bird_detections)
            
            # Test 3: With date range (problematic case)
            start_time = (datetime.now() - timedelta(hours=24)).isoformat() + 'Z'
            end_time = datetime.now().isoformat() + 'Z'
            
            response = client.get(
                f'/api/recent-detections?start={start_time}&end={end_time}&limit=50&sort=desc'
            )
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert 'detections' in data
            # Should exclude the 25-hour old detection
            assert len(data['detections']) <= 4
            
            # Test 4: With limit
            response = client.get('/api/recent-detections?limit=2')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert len(data['detections']) <= 2
    
    def test_recent_detections_endpoint_errors(self, test_app):
        """Test error scenarios for /api/recent-detections"""
        app, video_repo, detection_repo = test_app
        
        with app.test_client() as client:
            # Test 1: Invalid limit
            response = client.get('/api/recent-detections?limit=2000')
            assert response.status_code == 400
            
            data = json.loads(response.data)
            assert 'error' in data
            assert 'cannot exceed 1000' in data['error'].lower()
            
            # Test 2: Invalid date format
            response = client.get('/api/recent-detections?start=invalid-date')
            # This might return 500 depending on how SQLite handles it
            assert response.status_code in [400, 500]
            
            data = json.loads(response.data)
            assert 'error' in data
    
    def test_api_status_endpoint(self, test_app):
        """Test /api/status endpoint"""
        app, video_repo, detection_repo = test_app
        
        with app.test_client() as client:
            response = client.get('/api/status')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            
            # Check required fields
            required_fields = [
                'status', 'uptime', 'videos_today', 'detections_today',
                'storage_used', 'storage_total', 'queue', 'performance', 'system', 'totals'
            ]
            
            for field in required_fields:
                assert field in data, f"Missing field: {field}"
    
    def test_database_missing_tables_scenario(self, test_config, temp_storage):
        """Test API behavior when database has missing tables"""
        # Create empty database (no tables)
        empty_db_path = temp_storage / "empty.db"
        db_manager = DatabaseManager(str(empty_db_path))
        video_repo = VideoRepository(db_manager)
        detection_repo = DetectionRepository(db_manager)
        
        # Don't create tables - simulate the original bug
        
        processing_service = Mock()
        processing_service.model_manager = Mock()
        processing_service.model_manager.is_loaded = True
        
        app = create_processing_app(processing_service, video_repo, detection_repo, test_config)
        app.config['TESTING'] = True
        
        with app.test_client() as client:
            # This should return a 500 error with detailed information
            response = client.get('/api/recent-detections')
            assert response.status_code == 500
            
            data = json.loads(response.data)
            assert 'error' in data
            assert 'details' in data
            assert 'database_path' in data
    
    def test_file_serving_endpoints(self, test_app, temp_storage):
        """Test video and thumbnail serving endpoints"""
        app, video_repo, detection_repo = test_app
        
        # Create test files
        test_video = temp_storage / "processed" / "detections" / "test_video.mp4"
        test_video.write_bytes(b"fake video content")
        
        test_thumb = temp_storage / "thumbnails" / "test_thumb.jpg"
        test_thumb.write_bytes(b"fake thumbnail content")
        
        with app.test_client() as client:
            # Test video serving
            response = client.get('/videos/test_video.mp4')
            assert response.status_code == 200
            assert response.data == b"fake video content"
            
            # Test thumbnail serving
            response = client.get('/thumbnails/test_thumb.jpg')
            assert response.status_code == 200
            assert response.data == b"fake thumbnail content"
            
            # Test 404 for missing files
            response = client.get('/videos/nonexistent.mp4')
            assert response.status_code == 404
            
            response = client.get('/thumbnails/missing.jpg')
            assert response.status_code == 404
    
    def test_motion_settings_endpoints(self, test_app, temp_storage):
        """Test motion settings GET/POST endpoints"""
        app, video_repo, detection_repo = test_app
        
        with app.test_client() as client:
            # Test GET motion settings (should return defaults)
            response = client.get('/api/motion-settings')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert 'motion_threshold' in data
            assert 'min_contour_area' in data
            
            # Test POST motion settings
            new_settings = {
                'motion_threshold': 6000,
                'min_contour_area': 600,
                'motion_timeout_seconds': 45
            }
            
            response = client.post('/api/motion-settings', 
                                 data=json.dumps(new_settings),
                                 content_type='application/json')
            assert response.status_code == 200
            
            # Verify settings were saved
            settings_file = temp_storage / "motion_settings_camera_0.json"
            assert settings_file.exists()
            
            saved_settings = json.loads(settings_file.read_text())
            assert saved_settings['motion_threshold'] == 6000


if __name__ == '__main__':
    pytest.main([__file__, '-v'])