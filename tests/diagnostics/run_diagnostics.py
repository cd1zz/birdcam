#!/usr/bin/env python3
"""
Diagnostic test runner for BirdCam bug fixes
"""
import sys
import subprocess
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def run_diagnostic_tests():
    """Run all diagnostic tests and generate a report"""
    print("🔍 Running BirdCam Diagnostic Tests")
    print("=" * 50)
    
    test_files = [
        'test_camera_manager_fixes.py',
        'test_config_fixes.py', 
        'test_processing_service_fixes.py',
        'test_web_routes_fixes.py'
    ]
    
    results = {}
    
    for test_file in test_files:
        print(f"\n🧪 Running {test_file}")
        print("-" * 30)
        
        try:
            # Run pytest for this specific test file
            result = subprocess.run([
                sys.executable, '-m', 'pytest', 
                str(Path(__file__).parent / test_file),
                '-v', '--tb=short'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                results[test_file] = 'PASSED'
                print(f"✅ {test_file}: PASSED")
            else:
                results[test_file] = 'FAILED'
                print(f"❌ {test_file}: FAILED")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
                
        except Exception as e:
            results[test_file] = f'ERROR: {e}'
            print(f"💥 {test_file}: ERROR - {e}")
    
    # Generate summary report
    print("\n📊 DIAGNOSTIC TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for result in results.values() if result == 'PASSED')
    total = len(results)
    
    for test_file, result in results.items():
        status_icon = "✅" if result == 'PASSED' else "❌"
        print(f"{status_icon} {test_file}: {result}")
    
    print(f"\n📈 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All diagnostic tests passed! Bug fixes are working correctly.")
        return True
    else:
        print("⚠️  Some diagnostic tests failed. Please review the fixes.")
        return False

if __name__ == '__main__':
    success = run_diagnostic_tests()
    sys.exit(0 if success else 1)