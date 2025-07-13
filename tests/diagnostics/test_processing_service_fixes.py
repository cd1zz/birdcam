#!/usr/bin/env python3
"""
Test suite for processing service race condition fixes
"""
import pytest
import threading
import time
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.processing_service import ProcessingService
from config.settings import DetectionConfig, ProcessingConfig


class TestProcessingServiceRaceCondition:
    """Test processing service race condition fixes"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.detection_config = DetectionConfig(
            classes=['bird'],
            confidences={'bird': 0.35},
            model_name='yolov5n',
            process_every_nth_frame=3,
            max_thumbnails_per_video=5
        )
        
        self.processing_config = ProcessingConfig(
            storage_path=Path('/tmp/test_storage'),
            detection=self.detection_config,
            detection_retention_days=30,
            no_detection_retention_days=7
        )
    
    @patch('services.processing_service.AIModelManager')
    @patch('services.processing_service.VideoRepository')
    @patch('services.processing_service.DetectionRepository')
    def test_process_pending_videos_race_condition(self, mock_detection_repo, mock_video_repo, mock_model_manager):
        """Test that process_pending_videos handles race conditions correctly"""
        # Setup mocks
        mock_video_repo.get_pending_videos.return_value = [Mock()]
        mock_model_manager.is_loaded = True
        
        # Create processing service
        processing_service = ProcessingService(
            self.processing_config,
            mock_model_manager,
            mock_video_repo,
            mock_detection_repo
        )
        
        # Track number of actual processing calls
        process_count = 0
        original_process = processing_service._process_single_video
        
        def slow_process(*args, **kwargs):
            nonlocal process_count
            process_count += 1
            time.sleep(0.1)  # Simulate slow processing
            return original_process(*args, **kwargs)
        
        processing_service._process_single_video = slow_process
        
        # Start multiple threads trying to process
        threads = []
        for i in range(5):
            thread = threading.Thread(target=processing_service.process_pending_videos)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify that processing only happened once (no race condition)
        assert process_count <= 1, f"Expected at most 1 processing call, got {process_count}"
    
    @patch('services.processing_service.AIModelManager')
    @patch('services.processing_service.VideoRepository')
    @patch('services.processing_service.DetectionRepository')
    def test_process_pending_videos_no_pending_videos(self, mock_detection_repo, mock_video_repo, mock_model_manager):
        """Test that process_pending_videos handles no pending videos correctly"""
        # Setup mocks
        mock_video_repo.get_pending_videos.return_value = []
        
        # Create processing service
        processing_service = ProcessingService(
            self.processing_config,
            mock_model_manager,
            mock_video_repo,
            mock_detection_repo
        )
        
        # Call process_pending_videos
        processing_service.process_pending_videos()
        
        # Verify that is_processing remains False
        assert processing_service.is_processing is False
    
    @patch('services.processing_service.AIModelManager')
    @patch('services.processing_service.VideoRepository')
    @patch('services.processing_service.DetectionRepository')
    def test_process_pending_videos_already_processing(self, mock_detection_repo, mock_video_repo, mock_model_manager):
        """Test that process_pending_videos returns early if already processing"""
        # Setup mocks
        mock_video_repo.get_pending_videos.return_value = [Mock()]
        
        # Create processing service
        processing_service = ProcessingService(
            self.processing_config,
            mock_model_manager,
            mock_video_repo,
            mock_detection_repo
        )
        
        # Set is_processing to True
        processing_service.is_processing = True
        
        # Call process_pending_videos
        processing_service.process_pending_videos()
        
        # Verify that get_pending_videos was not called
        mock_video_repo.get_pending_videos.assert_not_called()
    
    @patch('services.processing_service.AIModelManager')
    @patch('services.processing_service.VideoRepository')
    @patch('services.processing_service.DetectionRepository')
    def test_processing_lock_acquisition(self, mock_detection_repo, mock_video_repo, mock_model_manager):
        """Test that processing lock is properly acquired"""
        # Setup mocks
        mock_video_repo.get_pending_videos.return_value = [Mock()]
        mock_model_manager.is_loaded = True
        
        # Create processing service
        processing_service = ProcessingService(
            self.processing_config,
            mock_model_manager,
            mock_video_repo,
            mock_detection_repo
        )
        
        # Verify that processing_lock exists and is a Lock
        assert hasattr(processing_service, 'processing_lock')
        assert isinstance(processing_service.processing_lock, threading.Lock)
        
        # Test that lock can be acquired
        acquired = processing_service.processing_lock.acquire(blocking=False)
        assert acquired is True
        processing_service.processing_lock.release()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])