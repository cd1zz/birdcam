#!/usr/bin/env python3
"""
Integration tests for database operations
Tests the complete database setup, queries, and error handling
"""

import pytest
import tempfile
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock

from database.connection import DatabaseManager
from database.repositories.video_repository import VideoRepository
from database.repositories.detection_repository import DetectionRepository
from core.models import VideoFile, BirdDetection


class TestDatabaseOperations:
    """Test database operations and error scenarios"""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        yield db_path
        
        # Cleanup
        Path(db_path).unlink(missing_ok=True)
    
    @pytest.fixture
    def db_manager(self, temp_db):
        """Create database manager with temporary database"""
        return DatabaseManager(temp_db)
    
    @pytest.fixture
    def repos(self, db_manager):
        """Create repository instances"""
        video_repo = VideoRepository(db_manager)
        detection_repo = DetectionRepository(db_manager)
        
        # Create tables
        video_repo.create_table()
        detection_repo.create_table()
        
        return video_repo, detection_repo
    
    def test_database_table_creation(self, repos):
        """Test that database tables are created correctly"""
        video_repo, detection_repo = repos
        
        # Verify tables exist
        with video_repo.db_manager.get_connection() as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            assert 'videos' in tables
            assert 'detections' in tables
    
    def test_video_crud_operations(self, repos):
        """Test video repository CRUD operations"""
        video_repo, _ = repos
        
        # Create test video
        video = VideoFile(
            filename="test_video.mp4",
            original_filename="original.mp4", 
            file_size=1024000,
            duration=120.5,
            fps=30.0,
            resolution="1920x1080",
            received_time=datetime.now(),
            status="pending"
        )
        
        # Test create
        video_id = video_repo.create(video)
        assert video_id is not None
        assert video_id > 0
        
        # Test read
        retrieved_video = video_repo.get_by_id(video_id)
        assert retrieved_video is not None
        assert retrieved_video.filename == "test_video.mp4"
        assert retrieved_video.status == "pending"
        
        # Test update
        video_repo.update_status(video_id, "completed")
        updated_video = video_repo.get_by_id(video_id)
        assert updated_video.status == "completed"
        
        # Test list
        all_videos = video_repo.get_all()
        assert len(all_videos) == 1
        assert all_videos[0].id == video_id
    
    def test_detection_crud_operations(self, repos):
        """Test detection repository CRUD operations"""
        video_repo, detection_repo = repos
        
        # Create test video first
        video = VideoFile(
            filename="test_video.mp4",
            original_filename="original.mp4",
            file_size=1024000,
            received_time=datetime.now(),
            status="completed"
        )
        video_id = video_repo.create(video)
        
        # Create test detection
        detection = BirdDetection(
            video_id=video_id,
            frame_number=150,
            timestamp=5.0,
            confidence=0.85,
            bbox=(100, 100, 200, 200),
            species="bird",
            thumbnail_path="thumb.jpg"
        )
        
        # Test create
        detection_id = detection_repo.create(detection)
        assert detection_id is not None
        assert detection_id > 0
        
        # Test read
        retrieved_detection = detection_repo.get_by_id(detection_id)
        assert retrieved_detection is not None
        assert retrieved_detection.species == "bird"
        assert retrieved_detection.confidence == 0.85
        assert retrieved_detection.bbox == (100, 100, 200, 200)
        
        # Test get by video
        video_detections = detection_repo.get_by_video_id(video_id)
        assert len(video_detections) == 1
        assert video_detections[0].id == detection_id
    
    def test_recent_detections_with_filtering(self, repos):
        """Test the problematic recent detections query with filtering"""
        video_repo, detection_repo = repos
        
        # Create test data with different timestamps and species
        base_time = datetime.now()
        test_data = [
            {"offset_hours": -2, "species": "bird", "confidence": 0.8},
            {"offset_hours": -4, "species": "cat", "confidence": 0.9},
            {"offset_hours": -6, "species": "bird", "confidence": 0.7},
            {"offset_hours": -25, "species": "dog", "confidence": 0.85},  # Outside 24h window
        ]
        
        for i, data in enumerate(test_data):
            # Create video
            video = VideoFile(
                filename=f"test_video_{i}.mp4",
                original_filename=f"original_{i}.mp4",
                file_size=1024000,
                received_time=base_time + timedelta(hours=data["offset_hours"]),
                status="completed"
            )
            video_id = video_repo.create(video)
            
            # Create detection
            detection = BirdDetection(
                video_id=video_id,
                frame_number=100,
                timestamp=1.0,
                confidence=data["confidence"],
                bbox=(50, 50, 150, 150),
                species=data["species"],
                thumbnail_path=f"thumb_{i}.jpg"
            )
            detection_repo.create(detection)
        
        # Test 1: Get all recent detections
        all_detections = detection_repo.get_recent_filtered_with_thumbnails(limit=10)
        assert len(all_detections) == 4
        
        # Test 2: Filter by species
        bird_detections = detection_repo.get_recent_filtered_with_thumbnails(
            species="bird", limit=10
        )
        assert len(bird_detections) == 2
        assert all(item['detection'].species == "bird" for item in bird_detections)
        
        # Test 3: Filter by date range (last 24 hours)
        start_time = (base_time - timedelta(hours=24)).isoformat()
        end_time = base_time.isoformat()
        
        recent_detections = detection_repo.get_recent_filtered_with_thumbnails(
            start=start_time, end=end_time, limit=10
        )
        assert len(recent_detections) == 3  # Should exclude the 25-hour old detection
        
        # Test 4: Problematic date format (ISO with Z timezone)
        start_iso = start_time.replace('+00:00', 'Z') if '+00:00' in start_time else start_time + 'Z'
        end_iso = end_time.replace('+00:00', 'Z') if '+00:00' in end_time else end_time + 'Z'
        
        iso_detections = detection_repo.get_recent_filtered_with_thumbnails(
            start=start_iso, end=end_iso, limit=10
        )
        # This should work the same as the previous test
        assert len(iso_detections) == 3
    
    def test_database_error_scenarios(self, temp_db):
        """Test database error handling scenarios"""
        
        # Test 1: Database file doesn't exist
        nonexistent_db = "/nonexistent/path/test.db"
        with pytest.raises(Exception):
            db_manager = DatabaseManager(nonexistent_db)
            with db_manager.get_connection() as conn:
                conn.execute("SELECT 1")
        
        # Test 2: Corrupted database
        # Create a file that looks like a database but isn't
        corrupted_db = temp_db + "_corrupted"
        Path(corrupted_db).write_text("This is not a database file")
        
        with pytest.raises(sqlite3.DatabaseError):
            db_manager = DatabaseManager(corrupted_db)
            with db_manager.get_connection() as conn:
                conn.execute("SELECT 1")
        
        # Cleanup
        Path(corrupted_db).unlink(missing_ok=True)
        
        # Test 3: Missing tables
        empty_db = temp_db + "_empty"
        db_manager = DatabaseManager(empty_db)
        detection_repo = DetectionRepository(db_manager)
        
        # This should fail because tables don't exist
        with pytest.raises(sqlite3.OperationalError):
            detection_repo.get_recent_filtered_with_thumbnails(limit=1)
        
        # Cleanup
        Path(empty_db).unlink(missing_ok=True)
    
    def test_invalid_query_parameters(self, repos):
        """Test handling of invalid query parameters"""
        video_repo, detection_repo = repos
        
        # Test invalid date formats
        with pytest.raises((ValueError, sqlite3.OperationalError)):
            detection_repo.get_recent_filtered_with_thumbnails(
                start="invalid-date", end="also-invalid"
            )
        
        # Test very large limit (should work but might be slow)
        results = detection_repo.get_recent_filtered_with_thumbnails(limit=999999)
        assert isinstance(results, list)  # Should return empty list, not error
        
        # Test negative limit (SQLite should handle this)
        results = detection_repo.get_recent_filtered_with_thumbnails(limit=-1)
        assert isinstance(results, list)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])