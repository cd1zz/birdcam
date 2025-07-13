#!/usr/bin/env python3
"""
Validation script to check that bug fixes have been applied correctly
"""
import sys
import re
from pathlib import Path

def validate_camera_manager_fixes():
    """Validate camera manager resource leak fixes"""
    print("🔍 Validating camera manager fixes...")
    
    file_path = Path(__file__).parent.parent.parent / "services" / "camera_manager.py"
    
    if not file_path.exists():
        print("❌ Camera manager file not found")
        return False
    
    content = file_path.read_text()
    
    # Check for improved error handling in read_frame
    if "print(f\"❌ Camera read error: {e}\")" in content:
        print("✅ Error logging added to read_frame")
    else:
        print("❌ Error logging missing in read_frame")
        return False
    
    # Check for recovery mechanism
    if "self.release()" in content and "self._initialize_camera()" in content:
        print("✅ Camera recovery mechanism implemented")
    else:
        print("❌ Camera recovery mechanism missing")
        return False
    
    # Check for finally block in release
    if "finally:" in content and "self.picam2 = None" in content:
        print("✅ Finally block in release method")
    else:
        print("❌ Finally block missing in release method")
        return False
    
    return True

def validate_config_fixes():
    """Validate configuration mutable default fixes"""
    print("🔍 Validating configuration fixes...")
    
    file_path = Path(__file__).parent.parent.parent / "config" / "settings.py"
    
    if not file_path.exists():
        print("❌ Settings file not found")
        return False
    
    content = file_path.read_text()
    
    # Check for copy() in get_list_env
    if "default.copy()" in content:
        print("✅ Mutable default fix applied")
    else:
        print("❌ Mutable default fix missing")
        return False
    
    # Check for Optional import
    if "Optional[List[str]]" in content:
        print("✅ Type hints improved")
    else:
        print("❌ Type hints not improved")
        return False
    
    return True

def validate_processing_service_fixes():
    """Validate processing service race condition fixes"""
    print("🔍 Validating processing service fixes...")
    
    file_path = Path(__file__).parent.parent.parent / "services" / "processing_service.py"
    
    if not file_path.exists():
        print("❌ Processing service file not found")
        return False
    
    content = file_path.read_text()
    
    # Check for lock acquisition before is_processing check
    pattern = r"with self\.processing_lock:\s+if self\.is_processing:"
    if re.search(pattern, content, re.MULTILINE):
        print("✅ Race condition fix applied")
    else:
        print("❌ Race condition fix missing")
        return False
    
    return True

def validate_web_routes_fixes():
    """Validate web routes timeout and validation fixes"""
    print("🔍 Validating web routes fixes...")
    
    file_path = Path(__file__).parent.parent.parent / "web" / "routes" / "capture_routes.py"
    
    if not file_path.exists():
        print("❌ Capture routes file not found")
        return False
    
    content = file_path.read_text()
    
    # Check for timeouts in requests
    if "timeout=30" in content:
        print("✅ Video request timeout added")
    else:
        print("❌ Video request timeout missing")
        return False
    
    if "timeout=10" in content:
        print("✅ Thumbnail request timeout added")
    else:
        print("❌ Thumbnail request timeout missing")
        return False
    
    # Check for coordinate validation
    if "Invalid region dimensions" in content:
        print("✅ Coordinate validation added")
    else:
        print("❌ Coordinate validation missing")
        return False
    
    # Check for parameter validation
    if "Motion threshold must be positive" in content:
        print("✅ Parameter validation added")
    else:
        print("❌ Parameter validation missing")
        return False
    
    return True

def main():
    """Run all validation checks"""
    print("🔍 BirdCam Bug Fix Validation")
    print("=" * 50)
    
    validators = [
        ("Camera Manager", validate_camera_manager_fixes),
        ("Configuration", validate_config_fixes),
        ("Processing Service", validate_processing_service_fixes),
        ("Web Routes", validate_web_routes_fixes)
    ]
    
    passed = 0
    total = len(validators)
    
    for name, validator in validators:
        print(f"\n📋 {name} Validation:")
        print("-" * 30)
        
        try:
            if validator():
                passed += 1
                print(f"✅ {name}: All fixes validated")
            else:
                print(f"❌ {name}: Some fixes missing")
        except Exception as e:
            print(f"💥 {name}: Validation error - {e}")
    
    print(f"\n📊 VALIDATION SUMMARY")
    print("=" * 50)
    print(f"📈 Overall: {passed}/{total} components validated")
    
    if passed == total:
        print("🎉 All bug fixes have been successfully applied!")
        return True
    else:
        print("⚠️  Some fixes may be incomplete. Please review the output above.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)