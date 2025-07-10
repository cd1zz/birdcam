#!/usr/bin/env python3
"""
Integration tests for cross-camera motion triggering
"""
import unittest
import time
import threading
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.motion_event_broadcaster import MotionEventBroadcaster, initialize_motion_broadcaster
from services.capture_service import CaptureService
from config.settings import CaptureConfig, MotionConfig


class TestCrossCameraMotion(unittest.TestCase):
    """Integration tests for cross-camera motion triggering"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Initialize broadcaster
        self.broadcaster = initialize_motion_broadcaster(cross_trigger_enabled=True, trigger_timeout=1.0)
        
        # Create mock configurations
        self.config1 = CaptureConfig(
            camera_id=1,
            camera_type='picamera2',
            stream_url='',
            segment_duration=300,
            fps=10,
            resolution=(640, 480),
            buffer_size=2,
            pre_motion_buffer_seconds=15
        )
        
        self.config2 = CaptureConfig(
            camera_id=2,
            camera_type='picamera2',
            stream_url='',
            segment_duration=300,
            fps=10,
            resolution=(640, 480),
            buffer_size=2,
            pre_motion_buffer_seconds=15
        )
        
        self.motion_config = MotionConfig(
            threshold=5000,
            min_contour_area=500,
            learning_rate=0.01,
            motion_timeout_seconds=30,
            max_segment_duration=300
        )
        
        # Track recording states
        self.recording_states = {}
        self.recording_calls = []
    
    def tearDown(self):
        """Clean up after tests"""
        self.broadcaster.clear_motion_state()
    
    def create_mock_capture_service(self, camera_id):
        """Create a mock capture service"""
        # Create mocks for dependencies
        mock_camera_manager = Mock()
        mock_motion_detector = Mock()
        mock_video_writer = Mock()
        mock_sync_service = Mock()
        mock_video_repo = Mock()
        
        # Create capture service with mocks
        with patch('services.capture_service.get_motion_broadcaster', return_value=self.broadcaster):
            capture_service = CaptureService(
                self.config1 if camera_id == 1 else self.config2,
                self.motion_config,
                mock_camera_manager,
                mock_motion_detector,
                mock_video_writer,
                mock_sync_service,
                mock_video_repo
            )
        
        # Track when _start_recording is called
        original_start_recording = capture_service._start_recording
        
        def mock_start_recording():
            self.recording_states[camera_id] = True
            self.recording_calls.append(camera_id)
            return original_start_recording()
        
        capture_service._start_recording = mock_start_recording
        capture_service.is_capturing = False  # Start in non-capturing state
        
        return capture_service
    
    def test_cross_camera_triggering(self):
        """Test that motion on one camera triggers recording on both cameras"""
        # Create two capture services
        service1 = self.create_mock_capture_service(1)
        service2 = self.create_mock_capture_service(2)
        
        # Simulate motion detection on camera 1
        service1.motion_broadcaster.report_motion(1, confidence=0.8)
        
        # Give a moment for the trigger to propagate
        time.sleep(0.1)
        
        # Both cameras should have been triggered
        self.assertIn(1, self.recording_calls)
        self.assertIn(2, self.recording_calls)
        
        # Check that cross-camera motion was handled
        self.assertEqual(len(self.recording_calls), 2)
    
    def test_motion_extension_on_cross_trigger(self):
        """Test that recording is extended when cross-camera motion is detected"""
        # Create capture service
        service1 = self.create_mock_capture_service(1)
        service2 = self.create_mock_capture_service(2)
        
        # Start recording on camera 2
        service2.is_capturing = True
        service2.last_motion_time = time.time()
        
        # Simulate motion on camera 1 (should extend recording on camera 2)
        service1.motion_broadcaster.report_motion(1, confidence=0.8)
        
        # Give a moment for the trigger to propagate
        time.sleep(0.1)
        
        # Camera 2's recording should have been extended (last_motion_time updated)
        self.assertGreater(service2.last_motion_time, time.time() - 1.0)
    
    def test_self_motion_not_cross_triggered(self):
        """Test that cameras don't cross-trigger themselves"""
        # Create capture service
        service1 = self.create_mock_capture_service(1)
        
        # Clear recording calls
        self.recording_calls.clear()
        
        # Simulate motion detection on camera 1
        service1.motion_broadcaster.report_motion(1, confidence=0.8)
        
        # Give a moment for processing
        time.sleep(0.1)
        
        # Camera 1 should only be triggered once (not cross-triggered by itself)
        camera1_calls = [call for call in self.recording_calls if call == 1]
        self.assertEqual(len(camera1_calls), 1)
    
    def test_broadcaster_statistics_with_multiple_cameras(self):
        """Test broadcaster statistics with multiple cameras"""
        # Create multiple capture services
        service1 = self.create_mock_capture_service(1)
        service2 = self.create_mock_capture_service(2)
        
        # Simulate motion on both cameras
        service1.motion_broadcaster.report_motion(1, confidence=0.8)
        service2.motion_broadcaster.report_motion(2, confidence=0.9)
        
        # Check statistics
        stats = self.broadcaster.get_statistics()
        self.assertEqual(stats['total_events'], 2)
        self.assertEqual(stats['registered_cameras'], 2)
        self.assertTrue(stats['cross_triggers'] >= 2)  # At least 2 cross-triggers
    
    def test_timeout_behavior_with_multiple_cameras(self):
        """Test timeout behavior with multiple cameras"""
        # Create capture services
        service1 = self.create_mock_capture_service(1)
        service2 = self.create_mock_capture_service(2)
        
        # Simulate motion on camera 1
        service1.motion_broadcaster.report_motion(1, confidence=0.8)
        
        # Check that motion is active
        self.assertTrue(self.broadcaster.is_motion_active())
        
        # Check active cameras
        active_cameras = self.broadcaster.get_active_cameras()
        self.assertIn(1, active_cameras)
        
        # Wait for timeout
        time.sleep(1.1)
        
        # Motion should no longer be active
        self.assertFalse(self.broadcaster.is_motion_active())
        
        # No cameras should be active
        active_cameras = self.broadcaster.get_active_cameras()
        self.assertEqual(len(active_cameras), 0)
    
    def test_cross_trigger_disable_enable(self):
        """Test disabling and enabling cross-camera triggering"""
        # Create capture services
        service1 = self.create_mock_capture_service(1)
        service2 = self.create_mock_capture_service(2)
        
        # Disable cross-triggering
        self.broadcaster.set_cross_trigger_enabled(False)
        
        # Clear recording calls
        self.recording_calls.clear()
        
        # Simulate motion on camera 1
        service1.motion_broadcaster.report_motion(1, confidence=0.8)
        
        # Give a moment for processing
        time.sleep(0.1)
        
        # Should still trigger cameras (broadcaster still calls callbacks)
        self.assertTrue(len(self.recording_calls) >= 1)
        
        # Re-enable cross-triggering
        self.broadcaster.set_cross_trigger_enabled(True)
        self.recording_calls.clear()
        
        # Simulate motion again
        service1.motion_broadcaster.report_motion(1, confidence=0.8)
        time.sleep(0.1)
        
        # Both cameras should be triggered
        self.assertEqual(len(self.recording_calls), 2)
    
    def test_concurrent_motion_detection(self):
        """Test concurrent motion detection from multiple cameras"""
        # Create capture services
        service1 = self.create_mock_capture_service(1)
        service2 = self.create_mock_capture_service(2)
        
        # Create threads to simulate concurrent motion
        def simulate_motion(camera_id, count):
            for i in range(count):
                self.broadcaster.report_motion(camera_id, confidence=0.8)
                time.sleep(0.01)  # Small delay
        
        # Start concurrent motion detection
        thread1 = threading.Thread(target=simulate_motion, args=(1, 5))
        thread2 = threading.Thread(target=simulate_motion, args=(2, 5))
        
        thread1.start()
        thread2.start()
        
        thread1.join()
        thread2.join()
        
        # Check that all events were recorded
        stats = self.broadcaster.get_statistics()
        self.assertEqual(stats['total_events'], 10)
        
        # Check that both cameras were triggered multiple times
        self.assertTrue(len(self.recording_calls) >= 10)


if __name__ == '__main__':
    unittest.main()