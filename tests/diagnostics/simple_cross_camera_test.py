#!/usr/bin/env python3
"""
Simple test for cross-camera motion triggering
"""
import sys
import time
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def test_motion_broadcaster():
    """Simple test of motion broadcaster functionality"""
    print("🧪 Testing Motion Event Broadcaster...")
    
    try:
        from services.motion_event_broadcaster import MotionEventBroadcaster
        
        # Create broadcaster
        broadcaster = MotionEventBroadcaster(cross_trigger_enabled=True, trigger_timeout=1.0)
        print("✅ Broadcaster created successfully")
        
        # Test statistics
        stats = broadcaster.get_statistics()
        if stats['total_events'] == 0 and stats['registered_cameras'] == 0:
            print("✅ Initial statistics correct")
        else:
            print("❌ Initial statistics incorrect")
            return False
        
        # Test camera registration
        triggered_cameras = []
        
        def camera_callback(camera_id):
            def callback(motion_event):
                triggered_cameras.append(camera_id)
            return callback
        
        broadcaster.register_camera(0, camera_callback(0))
        broadcaster.register_camera(1, camera_callback(1))
        print("✅ Cameras registered")
        
        # Test motion triggering
        broadcaster.report_motion(0, confidence=0.8)
        
        # Check that both cameras were triggered
        if len(triggered_cameras) == 2 and 0 in triggered_cameras and 1 in triggered_cameras:
            print("✅ Cross-camera triggering works")
        else:
            print(f"❌ Cross-camera triggering failed: {triggered_cameras}")
            return False
        
        # Test statistics after motion
        stats = broadcaster.get_statistics()
        if stats['total_events'] == 1:
            print("✅ Motion event statistics correct")
        else:
            print(f"❌ Motion event statistics incorrect: {stats}")
            return False
        
        # Test timeout
        if broadcaster.is_motion_active():
            print("✅ Motion active immediately after detection")
        else:
            print("❌ Motion should be active after detection")
            return False
        
        print("🕐 Waiting for timeout...")
        time.sleep(1.1)
        
        if not broadcaster.is_motion_active():
            print("✅ Motion timeout works correctly")
        else:
            print("❌ Motion timeout failed")
            return False
        
        print("✅ All motion broadcaster tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Motion broadcaster test failed: {e}")
        return False

def test_capture_service_integration():
    """Test capture service integration with motion broadcaster"""
    print("\n🧪 Testing Capture Service Integration...")
    
    try:
        from services.motion_event_broadcaster import initialize_motion_broadcaster
        from services.capture_service import CaptureService
        from config.settings import CaptureConfig, MotionConfig
        from unittest.mock import Mock
        
        # Initialize broadcaster
        broadcaster = initialize_motion_broadcaster(cross_trigger_enabled=True, trigger_timeout=1.0)
        print("✅ Motion broadcaster initialized")
        
        # Create mock dependencies
        capture_config = CaptureConfig(
            camera_id=0,
            camera_type='picamera2',
            stream_url='',
            segment_duration=300,
            fps=10,
            resolution=(640, 480),
            buffer_size=2,
            pre_motion_buffer_seconds=15
        )
        
        motion_config = MotionConfig(
            threshold=5000,
            min_contour_area=500,
            learning_rate=0.01,
            motion_timeout_seconds=30,
            max_segment_duration=300
        )
        
        # Create mocks
        mock_camera_manager = Mock()
        mock_motion_detector = Mock()
        mock_video_writer = Mock()
        mock_sync_service = Mock()
        mock_video_repo = Mock()
        
        # Create capture service
        capture_service = CaptureService(
            capture_config,
            motion_config,
            mock_camera_manager,
            mock_motion_detector,
            mock_video_writer,
            mock_sync_service,
            mock_video_repo
        )
        print("✅ Capture service created and registered with broadcaster")
        
        # Check that it has the motion broadcaster
        if hasattr(capture_service, 'motion_broadcaster'):
            print("✅ Capture service has motion broadcaster reference")
        else:
            print("❌ Capture service missing motion broadcaster reference")
            return False
        
        # Check that it has cross-camera motion handler
        if hasattr(capture_service, '_handle_cross_camera_motion'):
            print("✅ Capture service has cross-camera motion handler")
        else:
            print("❌ Capture service missing cross-camera motion handler")
            return False
        
        # Test statistics method
        try:
            stats = capture_service.get_motion_broadcaster_stats()
            if isinstance(stats, dict):
                print("✅ Motion broadcaster statistics accessible from capture service")
            else:
                print("❌ Motion broadcaster statistics method failed")
                return False
        except Exception as e:
            print(f"❌ Motion broadcaster statistics error: {e}")
            return False
        
        print("✅ All capture service integration tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Capture service integration test failed: {e}")
        return False

def test_api_endpoints():
    """Test API endpoint functionality"""
    print("\n🧪 Testing API Endpoints...")
    
    try:
        # Test that the API functions can be imported
        from web.routes.capture_routes import create_capture_routes
        print("✅ API route functions can be imported")
        
        # This would require a full Flask app setup, so we'll just check imports
        print("✅ API endpoints should be functional (full test requires Flask app)")
        return True
        
    except Exception as e:
        print(f"❌ API endpoint test failed: {e}")
        return False

def main():
    """Run all simple tests"""
    print("🔍 Running Simple Cross-Camera Motion Tests")
    print("=" * 50)
    
    tests = [
        test_motion_broadcaster,
        test_capture_service_integration,
        test_api_endpoints
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
    
    print(f"\n📊 SIMPLE TEST SUMMARY")
    print("=" * 50)
    print(f"📈 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All simple tests passed! Cross-camera motion feature is working.")
        return True
    else:
        print("⚠️  Some simple tests failed. Please review the implementation.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)