#!/usr/bin/env python3
"""
Unit tests for motion event broadcaster
"""
import unittest
import time
import threading
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.motion_event_broadcaster import MotionEventBroadcaster, MotionEvent


class TestMotionEventBroadcaster(unittest.TestCase):
    """Test the motion event broadcaster functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.broadcaster = MotionEventBroadcaster(cross_trigger_enabled=True, trigger_timeout=1.0)
        self.motion_events = []
        self.triggered_cameras = []
    
    def tearDown(self):
        """Clean up after tests"""
        self.broadcaster.clear_motion_state()
    
    def mock_motion_callback(self, camera_id):
        """Mock motion callback for testing"""
        def callback(motion_event):
            self.motion_events.append(motion_event)
            self.triggered_cameras.append(camera_id)
        return callback
    
    def test_camera_registration(self):
        """Test camera registration and unregistration"""
        # Test registration
        callback = self.mock_motion_callback(1)
        self.broadcaster.register_camera(1, callback)
        
        stats = self.broadcaster.get_statistics()
        self.assertEqual(stats['registered_cameras'], 1)
        
        # Test unregistration
        self.broadcaster.unregister_camera(1)
        stats = self.broadcaster.get_statistics()
        self.assertEqual(stats['registered_cameras'], 0)
    
    def test_motion_detection_broadcasting(self):
        """Test that motion events are broadcast to all cameras"""
        # Register multiple cameras
        self.broadcaster.register_camera(1, self.mock_motion_callback(1))
        self.broadcaster.register_camera(2, self.mock_motion_callback(2))
        
        # Report motion from camera 1
        self.broadcaster.report_motion(1, confidence=0.8)
        
        # Both cameras should be triggered
        self.assertEqual(len(self.triggered_cameras), 2)
        self.assertIn(1, self.triggered_cameras)
        self.assertIn(2, self.triggered_cameras)
        
        # Check that motion events were recorded
        self.assertEqual(len(self.motion_events), 2)
        self.assertTrue(all(event.camera_id == 1 for event in self.motion_events))
    
    def test_cross_trigger_enabled_disabled(self):
        """Test enabling/disabling cross-camera triggering"""
        # Register cameras
        self.broadcaster.register_camera(1, self.mock_motion_callback(1))
        self.broadcaster.register_camera(2, self.mock_motion_callback(2))
        
        # Disable cross-triggering
        self.broadcaster.set_cross_trigger_enabled(False)
        
        # Report motion from camera 1
        self.broadcaster.report_motion(1, confidence=0.8)
        
        # Should still trigger (cross-trigger logic doesn't prevent self-triggering)
        self.assertTrue(len(self.triggered_cameras) >= 1)
        
        # Re-enable cross-triggering
        self.broadcaster.set_cross_trigger_enabled(True)
        self.motion_events.clear()
        self.triggered_cameras.clear()
        
        # Report motion again
        self.broadcaster.report_motion(1, confidence=0.8)
        
        # Both cameras should be triggered again
        self.assertEqual(len(self.triggered_cameras), 2)
    
    def test_motion_timeout(self):
        """Test motion timeout functionality"""
        # Register camera
        self.broadcaster.register_camera(1, self.mock_motion_callback(1))
        
        # Report motion
        self.broadcaster.report_motion(1, confidence=0.8)
        
        # Check that motion is active
        self.assertTrue(self.broadcaster.is_motion_active())
        
        # Wait for timeout
        time.sleep(1.1)  # Slightly longer than timeout
        
        # Motion should no longer be active
        self.assertFalse(self.broadcaster.is_motion_active())
    
    def test_active_cameras_tracking(self):
        """Test tracking of active cameras"""
        # Register cameras
        self.broadcaster.register_camera(1, self.mock_motion_callback(1))
        self.broadcaster.register_camera(2, self.mock_motion_callback(2))
        
        # Report motion from camera 1
        self.broadcaster.report_motion(1, confidence=0.8)
        
        # Camera 1 should be active
        active_cameras = self.broadcaster.get_active_cameras()
        self.assertIn(1, active_cameras)
        
        # Report motion from camera 2
        self.broadcaster.report_motion(2, confidence=0.9)
        
        # Both cameras should be active
        active_cameras = self.broadcaster.get_active_cameras()
        self.assertIn(1, active_cameras)
        self.assertIn(2, active_cameras)
        
        # Wait for timeout
        time.sleep(1.1)
        
        # No cameras should be active after timeout
        active_cameras = self.broadcaster.get_active_cameras()
        self.assertEqual(len(active_cameras), 0)
    
    def test_statistics_tracking(self):
        """Test statistics tracking"""
        # Register cameras
        self.broadcaster.register_camera(1, self.mock_motion_callback(1))
        self.broadcaster.register_camera(2, self.mock_motion_callback(2))
        
        # Report motion events
        self.broadcaster.report_motion(1, confidence=0.8)
        self.broadcaster.report_motion(2, confidence=0.9)
        
        # Check statistics
        stats = self.broadcaster.get_statistics()
        self.assertEqual(stats['total_events'], 2)
        self.assertEqual(stats['registered_cameras'], 2)
        self.assertTrue(stats['cross_triggers'] >= 2)  # At least 2 cross-triggers
    
    def test_thread_safety(self):
        """Test thread safety of the broadcaster"""
        # Register cameras
        self.broadcaster.register_camera(1, self.mock_motion_callback(1))
        self.broadcaster.register_camera(2, self.mock_motion_callback(2))
        
        # Create multiple threads to report motion simultaneously
        threads = []
        for i in range(10):
            thread = threading.Thread(
                target=self.broadcaster.report_motion,
                args=(1, 0.8)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check that all events were recorded
        stats = self.broadcaster.get_statistics()
        self.assertEqual(stats['total_events'], 10)
    
    def test_motion_event_properties(self):
        """Test motion event properties"""
        # Register camera
        self.broadcaster.register_camera(1, self.mock_motion_callback(1))
        
        # Report motion with specific properties
        self.broadcaster.report_motion(1, confidence=0.85, location=(100, 200))
        
        # Check that event has correct properties
        self.assertEqual(len(self.motion_events), 1)
        event = self.motion_events[0]
        self.assertEqual(event.camera_id, 1)
        self.assertEqual(event.confidence, 0.85)
        self.assertEqual(event.location, (100, 200))
        self.assertIsInstance(event.timestamp, float)


if __name__ == '__main__':
    unittest.main()