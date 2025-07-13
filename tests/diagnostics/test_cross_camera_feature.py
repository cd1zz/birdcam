#!/usr/bin/env python3
"""
Diagnostic tests for cross-camera motion triggering feature
"""
import unittest
import time
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.motion_event_broadcaster import MotionEventBroadcaster, get_motion_broadcaster


class TestCrossCameraFeatureDiagnostics(unittest.TestCase):
    """Diagnostic tests for cross-camera motion triggering feature"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a fresh broadcaster for each test
        self.broadcaster = MotionEventBroadcaster(cross_trigger_enabled=True, trigger_timeout=2.0)
        self.triggered_cameras = []
        self.trigger_count = 0
    
    def tearDown(self):
        """Clean up after tests"""
        self.broadcaster.clear_motion_state()
    
    def motion_callback(self, camera_id):
        """Mock motion callback that tracks triggers"""
        def callback(motion_event):
            self.triggered_cameras.append(camera_id)
            self.trigger_count += 1
        return callback
    
    def test_feature_initialization(self):
        """Test that cross-camera feature initializes correctly"""
        # Test broadcaster creation
        self.assertIsNotNone(self.broadcaster)
        self.assertTrue(self.broadcaster.cross_trigger_enabled)
        self.assertEqual(self.broadcaster.trigger_timeout, 2.0)
        
        # Test statistics initialization
        stats = self.broadcaster.get_statistics()
        self.assertEqual(stats['total_events'], 0)
        self.assertEqual(stats['cross_triggers'], 0)
        self.assertEqual(stats['registered_cameras'], 0)
        self.assertFalse(stats['global_motion_active'])
        
        print("✅ Cross-camera feature initializes correctly")
    
    def test_camera_registration_system(self):
        """Test camera registration and management"""
        # Register cameras
        self.broadcaster.register_camera(0, self.motion_callback(0))
        self.broadcaster.register_camera(1, self.motion_callback(1))
        
        # Check registration
        stats = self.broadcaster.get_statistics()
        self.assertEqual(stats['registered_cameras'], 2)
        
        # Test unregistration
        self.broadcaster.unregister_camera(0)
        stats = self.broadcaster.get_statistics()
        self.assertEqual(stats['registered_cameras'], 1)
        
        print("✅ Camera registration system works correctly")
    
    def test_cross_camera_motion_triggering(self):
        """Test that motion on one camera triggers others"""
        # Register two cameras
        self.broadcaster.register_camera(0, self.motion_callback(0))
        self.broadcaster.register_camera(1, self.motion_callback(1))
        
        # Report motion from camera 0
        self.broadcaster.report_motion(0, confidence=0.8)
        
        # Both cameras should be triggered
        self.assertIn(0, self.triggered_cameras)
        self.assertIn(1, self.triggered_cameras)
        self.assertEqual(self.trigger_count, 2)
        
        # Check statistics
        stats = self.broadcaster.get_statistics()
        self.assertEqual(stats['total_events'], 1)
        self.assertEqual(stats['cross_triggers'], 1)  # One cross-trigger (camera 1)
        
        print("✅ Cross-camera motion triggering works correctly")
    
    def test_motion_state_tracking(self):
        """Test motion state tracking and timeout"""
        # Register camera
        self.broadcaster.register_camera(0, self.motion_callback(0))
        
        # Report motion
        self.broadcaster.report_motion(0, confidence=0.9)
        
        # Motion should be active
        self.assertTrue(self.broadcaster.is_motion_active())
        
        # Camera 0 should be in active cameras
        active_cameras = self.broadcaster.get_active_cameras()
        self.assertIn(0, active_cameras)
        
        # Wait for timeout (2 seconds + buffer)
        time.sleep(2.1)
        
        # Motion should no longer be active
        self.assertFalse(self.broadcaster.is_motion_active())
        
        # No cameras should be active
        active_cameras = self.broadcaster.get_active_cameras()
        self.assertEqual(len(active_cameras), 0)
        
        print("✅ Motion state tracking and timeout work correctly")
    
    def test_configuration_changes(self):
        """Test runtime configuration changes"""
        # Test enabling/disabling cross-triggering
        self.broadcaster.set_cross_trigger_enabled(False)
        self.assertFalse(self.broadcaster.cross_trigger_enabled)
        
        self.broadcaster.set_cross_trigger_enabled(True)
        self.assertTrue(self.broadcaster.cross_trigger_enabled)
        
        # Test timeout changes
        self.broadcaster.set_trigger_timeout(5.0)
        self.assertEqual(self.broadcaster.trigger_timeout, 5.0)
        
        print("✅ Configuration changes work correctly")
    
    def test_multiple_camera_scenario(self):
        """Test realistic multiple camera scenario"""
        # Register 3 cameras
        for i in range(3):
            self.broadcaster.register_camera(i, self.motion_callback(i))
        
        # Report motion from camera 1
        self.broadcaster.report_motion(1, confidence=0.7, location=(100, 200))
        
        # All 3 cameras should be triggered
        self.assertEqual(len(self.triggered_cameras), 3)
        self.assertIn(0, self.triggered_cameras)
        self.assertIn(1, self.triggered_cameras)
        self.assertIn(2, self.triggered_cameras)
        
        # Check statistics
        stats = self.broadcaster.get_statistics()
        self.assertEqual(stats['total_events'], 1)
        self.assertEqual(stats['cross_triggers'], 2)  # Two cross-triggers (cameras 0 and 2)
        self.assertEqual(stats['registered_cameras'], 3)
        
        print("✅ Multiple camera scenario works correctly")
    
    def test_concurrent_motion_events(self):
        """Test handling of concurrent motion events"""
        # Register 2 cameras
        self.broadcaster.register_camera(0, self.motion_callback(0))
        self.broadcaster.register_camera(1, self.motion_callback(1))
        
        # Report motion from both cameras quickly
        self.broadcaster.report_motion(0, confidence=0.8)
        self.broadcaster.report_motion(1, confidence=0.9)
        
        # Should have triggered both cameras twice (once for each motion event)
        self.assertEqual(self.trigger_count, 4)  # 2 cameras × 2 events
        
        # Check statistics
        stats = self.broadcaster.get_statistics()
        self.assertEqual(stats['total_events'], 2)
        self.assertEqual(stats['cross_triggers'], 2)
        
        print("✅ Concurrent motion events handled correctly")
    
    def test_feature_performance(self):
        """Test performance with many motion events"""
        # Register 2 cameras
        self.broadcaster.register_camera(0, self.motion_callback(0))
        self.broadcaster.register_camera(1, self.motion_callback(1))
        
        # Report many motion events quickly
        start_time = time.time()
        for i in range(100):
            self.broadcaster.report_motion(0, confidence=0.8)
        end_time = time.time()
        
        # Should complete quickly (under 1 second)
        duration = end_time - start_time
        self.assertLess(duration, 1.0)
        
        # Check that all events were processed
        stats = self.broadcaster.get_statistics()
        self.assertEqual(stats['total_events'], 100)
        
        print(f"✅ Performance test passed: {100} events processed in {duration:.3f}s")
    
    def test_error_handling(self):
        """Test error handling in callbacks"""
        def faulty_callback(motion_event):
            raise Exception("Callback error")
        
        # Register cameras with one faulty callback
        self.broadcaster.register_camera(0, self.motion_callback(0))
        self.broadcaster.register_camera(1, faulty_callback)
        
        # Report motion (should not crash despite faulty callback)
        self.broadcaster.report_motion(0, confidence=0.8)
        
        # Good callback should still work
        self.assertIn(0, self.triggered_cameras)
        
        # Statistics should still be tracked
        stats = self.broadcaster.get_statistics()
        self.assertEqual(stats['total_events'], 1)
        
        print("✅ Error handling works correctly")
    
    def test_global_broadcaster_singleton(self):
        """Test that global broadcaster singleton works"""
        # Get global broadcaster
        global_broadcaster = get_motion_broadcaster()
        
        # Should be the same instance when called again
        global_broadcaster2 = get_motion_broadcaster()
        self.assertIs(global_broadcaster, global_broadcaster2)
        
        print("✅ Global broadcaster singleton works correctly")


def run_comprehensive_diagnostics():
    """Run comprehensive diagnostics for cross-camera feature"""
    print("🔍 Running Cross-Camera Motion Feature Diagnostics")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCrossCameraFeatureDiagnostics)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n📊 DIAGNOSTIC SUMMARY")
    print("=" * 60)
    
    if result.wasSuccessful():
        print("🎉 All cross-camera motion feature diagnostics passed!")
        print("✅ Feature is working correctly and ready for use")
        return True
    else:
        print("❌ Some diagnostics failed")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
        return False


if __name__ == '__main__':
    success = run_comprehensive_diagnostics()
    sys.exit(0 if success else 1)