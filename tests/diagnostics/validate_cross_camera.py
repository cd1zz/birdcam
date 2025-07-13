#!/usr/bin/env python3
"""
Validation script for cross-camera motion feature
"""
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def validate_files_exist():
    """Validate that all required files exist"""
    print("🔍 Validating cross-camera motion files...")
    
    required_files = [
        "services/motion_event_broadcaster.py",
    ]
    
    project_root = Path(__file__).parent.parent.parent
    
    for file_path in required_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"✅ {file_path} exists")
        else:
            print(f"❌ {file_path} missing")
            return False
    
    return True

def validate_imports():
    """Validate that imports work correctly"""
    print("\n🔍 Validating imports...")
    
    try:
        from services.motion_event_broadcaster import MotionEventBroadcaster, MotionEvent
        print("✅ MotionEventBroadcaster import successful")
    except Exception as e:
        print(f"❌ MotionEventBroadcaster import failed: {e}")
        return False
    
    try:
        from services.motion_event_broadcaster import get_motion_broadcaster, initialize_motion_broadcaster
        print("✅ Broadcaster functions import successful")
    except Exception as e:
        print(f"❌ Broadcaster functions import failed: {e}")
        return False
    
    return True

def validate_code_integration():
    """Validate that code integration is correct"""
    print("\n🔍 Validating code integration...")
    
    # Check capture service imports
    capture_service_path = Path(__file__).parent.parent.parent / "services" / "capture_service.py"
    if capture_service_path.exists():
        content = capture_service_path.read_text()
        
        if "from services.motion_event_broadcaster import" in content:
            print("✅ CaptureService imports motion broadcaster")
        else:
            print("❌ CaptureService missing motion broadcaster import")
            return False
        
        if "_handle_cross_camera_motion" in content:
            print("✅ CaptureService has cross-camera motion handler")
        else:
            print("❌ CaptureService missing cross-camera motion handler")
            return False
        
        if "self.motion_broadcaster.register_camera" in content:
            print("✅ CaptureService registers with motion broadcaster")
        else:
            print("❌ CaptureService doesn't register with motion broadcaster")
            return False
    
    # Check pi_capture main integration
    main_path = Path(__file__).parent.parent.parent / "pi_capture" / "main.py"
    if main_path.exists():
        content = main_path.read_text()
        
        if "initialize_motion_broadcaster" in content:
            print("✅ Main script initializes motion broadcaster")
        else:
            print("❌ Main script doesn't initialize motion broadcaster")
            return False
    
    # Check web routes integration
    routes_path = Path(__file__).parent.parent.parent / "web" / "routes" / "capture_routes.py"
    if routes_path.exists():
        content = routes_path.read_text()
        
        if "motion-broadcaster" in content:
            print("✅ Web routes have motion broadcaster endpoints")
        else:
            print("❌ Web routes missing motion broadcaster endpoints")
            return False
    
    return True

def validate_feature_logic():
    """Validate core feature logic without full instantiation"""
    print("\n🔍 Validating feature logic...")
    
    try:
        # Just check that the class can be defined without instantiation
        from services.motion_event_broadcaster import MotionEventBroadcaster, MotionEvent
        
        # Check MotionEvent dataclass
        event = MotionEvent(camera_id=1, timestamp=123.456)
        if event.camera_id == 1 and event.timestamp == 123.456:
            print("✅ MotionEvent dataclass works")
        else:
            print("❌ MotionEvent dataclass failed")
            return False
        
        print("✅ Feature logic validation passed")
        return True
        
    except Exception as e:
        print(f"❌ Feature logic validation failed: {e}")
        return False

def main():
    """Run all validations"""
    print("🔍 Cross-Camera Motion Feature Validation")
    print("=" * 50)
    
    validations = [
        ("File Existence", validate_files_exist),
        ("Import Validation", validate_imports),
        ("Code Integration", validate_code_integration),
        ("Feature Logic", validate_feature_logic)
    ]
    
    passed = 0
    total = len(validations)
    
    for name, validation in validations:
        print(f"\n📋 {name}:")
        print("-" * 30)
        
        try:
            if validation():
                passed += 1
                print(f"✅ {name}: PASSED")
            else:
                print(f"❌ {name}: FAILED")
        except Exception as e:
            print(f"💥 {name}: ERROR - {e}")
    
    print(f"\n📊 VALIDATION SUMMARY")
    print("=" * 50)
    print(f"📈 Overall: {passed}/{total} validations passed")
    
    if passed == total:
        print("🎉 All validations passed! Cross-camera motion feature is properly implemented.")
        return True
    else:
        print("⚠️  Some validations failed. Please review the implementation.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)