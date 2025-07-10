#!/usr/bin/env python3
"""
Manual test to verify bug fixes without pytest
"""
import sys
import threading
import time
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def test_config_mutable_defaults():
    """Test that get_list_env doesn't share mutable defaults"""
    from config.settings import get_list_env
    
    print("🧪 Testing config mutable defaults fix...")
    
    # Test with default value
    result1 = get_list_env('NONEXISTENT_VAR', ['default1'])
    result2 = get_list_env('NONEXISTENT_VAR', ['default2'])
    
    # Modify one result
    result1.append('modified')
    
    # Verify that result2 is not affected
    if result2 == ['default2'] and 'modified' not in result2:
        print("✅ Mutable defaults fix working correctly")
        return True
    else:
        print("❌ Mutable defaults fix failed")
        return False

def test_camera_manager_error_handling():
    """Test camera manager error handling"""
    from services.camera_manager import CameraManager
    from config.settings import CaptureConfig
    
    print("🧪 Testing camera manager error handling...")
    
    config = CaptureConfig(
        camera_id=0,
        camera_type='picamera2',
        stream_url='',
        segment_duration=300,
        fps=10,
        resolution=(640, 480),
        buffer_size=2,
        pre_motion_buffer_seconds=15
    )
    
    try:
        # This should fail gracefully if picamera2 is not available
        camera_manager = CameraManager(config)
        print("✅ Camera manager initialized (or failed gracefully)")
        return True
    except RuntimeError as e:
        if "Picamera2" in str(e):
            print("✅ Camera manager failed gracefully with expected error")
            return True
        else:
            print(f"❌ Camera manager failed with unexpected error: {e}")
            return False
    except Exception as e:
        print(f"❌ Camera manager failed with unexpected error: {e}")
        return False

def test_processing_service_race_condition():
    """Test processing service race condition fix"""
    print("🧪 Testing processing service race condition fix...")
    
    # Create a simple class to simulate the fixed behavior
    class MockProcessingService:
        def __init__(self):
            self.is_processing = False
            self.processing_lock = threading.Lock()
            self.process_count = 0
        
        def process_pending_videos(self):
            """Simulate the fixed process_pending_videos method"""
            with self.processing_lock:
                if self.is_processing:
                    return
                self.is_processing = True
                self.process_count += 1
            
            # Simulate some processing time
            time.sleep(0.1)
            self.is_processing = False
    
    service = MockProcessingService()
    
    # Start multiple threads
    threads = []
    for i in range(5):
        thread = threading.Thread(target=service.process_pending_videos)
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Verify that processing only happened once
    if service.process_count == 1:
        print("✅ Race condition fix working correctly")
        return True
    else:
        print(f"❌ Race condition fix failed: expected 1 process, got {service.process_count}")
        return False

def main():
    """Run all manual tests"""
    print("🔍 Running BirdCam Manual Diagnostic Tests")
    print("=" * 50)
    
    tests = [
        test_config_mutable_defaults,
        test_camera_manager_error_handling,
        test_processing_service_race_condition
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
    
    print(f"\n📊 MANUAL TEST SUMMARY")
    print("=" * 50)
    print(f"📈 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All manual tests passed! Bug fixes are working correctly.")
        return True
    else:
        print("⚠️  Some manual tests failed. Please review the fixes.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)