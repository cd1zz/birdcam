#!/usr/bin/env python3
"""
Test suite for camera manager resource leak fixes
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.camera_manager import CameraManager
from config.settings import CaptureConfig


class TestCameraManagerResourceLeaks:
    """Test camera manager resource leak fixes"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.config = CaptureConfig(
            camera_id=0,
            camera_type='picamera2',
            stream_url='',
            segment_duration=300,
            fps=10,
            resolution=(640, 480),
            buffer_size=2,
            pre_motion_buffer_seconds=15
        )
    
    @patch('services.camera_manager.Picamera2')
    def test_camera_read_error_recovery(self, mock_picamera2_class):
        """Test that camera read errors trigger recovery"""
        # Setup mock
        mock_picam2 = Mock()
        mock_picamera2_class.return_value = mock_picam2
        
        # First call succeeds, second fails with exception
        mock_picam2.capture_array.side_effect = [
            Exception("Camera disconnected"),
            Exception("Still broken")
        ]
        
        # Create camera manager
        camera_manager = CameraManager(self.config)
        
        # Test that read_frame handles exception and attempts recovery
        success, frame = camera_manager.read_frame()
        assert success is False
        assert frame is None
        
        # Verify that release was called during recovery
        mock_picam2.close.assert_called()
    
    @patch('services.camera_manager.Picamera2')
    def test_camera_release_error_handling(self, mock_picamera2_class):
        """Test that camera release errors are handled gracefully"""
        # Setup mock
        mock_picam2 = Mock()
        mock_picamera2_class.return_value = mock_picam2
        
        # Make close() raise an exception
        mock_picam2.close.side_effect = Exception("Release error")
        
        # Create camera manager
        camera_manager = CameraManager(self.config)
        
        # Test that release handles exception gracefully
        camera_manager.release()
        
        # Verify that close was called and picam2 was set to None
        mock_picam2.close.assert_called_once()
        assert camera_manager.picam2 is None
    
    @patch('services.camera_manager.Picamera2')
    def test_camera_initialization_failure(self, mock_picamera2_class):
        """Test camera initialization failure handling"""
        # Make Picamera2 constructor raise an exception
        mock_picamera2_class.side_effect = Exception("Hardware not available")
        
        # Test that initialization failure is handled
        with pytest.raises(RuntimeError, match="Failed to initialize Picamera2"):
            CameraManager(self.config)
    
    @patch('services.camera_manager.Picamera2')
    def test_camera_resource_cleanup_on_exception(self, mock_picamera2_class):
        """Test that camera resources are properly cleaned up on exceptions"""
        # Setup mock
        mock_picam2 = Mock()
        mock_picamera2_class.return_value = mock_picam2
        
        # Make capture_array raise an exception
        mock_picam2.capture_array.side_effect = Exception("Capture failed")
        
        # Create camera manager
        camera_manager = CameraManager(self.config)
        
        # Call read_frame multiple times to trigger recovery
        for _ in range(3):
            success, frame = camera_manager.read_frame()
            assert success is False
            assert frame is None
        
        # Verify that close was called multiple times during recovery attempts
        assert mock_picam2.close.call_count >= 3


if __name__ == '__main__':
    pytest.main([__file__, '-v'])