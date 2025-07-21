#!/usr/bin/env python3
"""
Comprehensive test runner for the BirdCam system
Runs unit tests, integration tests, and system validation
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and return success status"""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent)
        
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
            return True
        else:
            print(f"❌ {description} - FAILED (exit code: {result.returncode})")
            return False
            
    except FileNotFoundError:
        print(f"❌ {description} - FAILED (command not found)")
        return False
    except Exception as e:
        print(f"❌ {description} - FAILED ({e})")
        return False


def main():
    parser = argparse.ArgumentParser(description='Run BirdCam test suite')
    parser.add_argument('--unit', action='store_true', help='Run only unit tests')
    parser.add_argument('--integration', action='store_true', help='Run only integration tests')
    parser.add_argument('--coverage', action='store_true', help='Run with coverage report')
    parser.add_argument('--html', action='store_true', help='Generate HTML report')
    parser.add_argument('--parallel', action='store_true', help='Run tests in parallel')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # If no specific test type selected, run all
    if not args.unit and not args.integration:
        args.unit = True
        args.integration = True
    
    print("🚀 Starting BirdCam Comprehensive Test Suite")
    print(f"📁 Working directory: {Path.cwd()}")
    
    results = []
    
    # Check if pytest is available
    check_cmd = [sys.executable, '-m', 'pytest', '--version']
    if not run_command(check_cmd, "Checking pytest availability"):
        print("\n❌ pytest not available. Install with: pip install -r tests/requirements.txt")
        return 1
    
    # Base pytest command
    base_cmd = [sys.executable, '-m', 'pytest']
    
    if args.verbose:
        base_cmd.append('-v')
    
    if args.coverage:
        base_cmd.extend(['--cov=.', '--cov-report=term-missing'])
        if args.html:
            base_cmd.append('--cov-report=html')
    
    if args.html:
        base_cmd.extend(['--html=test_report.html', '--self-contained-html'])
    
    if args.parallel:
        base_cmd.extend(['-n', 'auto'])  # Requires pytest-xdist
    
    # Run unit tests
    if args.unit:
        unit_cmd = base_cmd + ['tests/unit/', '-k', 'not integration']
        results.append(run_command(unit_cmd, "Unit Tests"))
    
    # Run integration tests
    if args.integration:
        integration_cmd = base_cmd + ['tests/integration/']
        results.append(run_command(integration_cmd, "Integration Tests"))
    
    # Run startup validation test
    validation_cmd = [sys.executable, '-c', '''
import sys
sys.path.append(".")
from config.settings import load_processing_config
from services.startup_validator import validate_startup

print("🔍 Testing startup validation...")
try:
    config = load_processing_config()
    result = validate_startup(config)
    if result:
        print("✅ Startup validation test passed")
        sys.exit(0)
    else:
        print("❌ Startup validation test failed")
        sys.exit(1)
except Exception as e:
    print(f"❌ Startup validation test error: {e}")
    sys.exit(1)
''']
    results.append(run_command(validation_cmd, "Startup Validation Test"))
    
    # Test database operations with real config
    db_test_cmd = [sys.executable, '-c', '''
import sys
sys.path.append(".")
from config.settings import load_processing_config
from database.connection import DatabaseManager
from database.repositories.detection_repository import DetectionRepository

print("🔍 Testing database operations with real config...")
try:
    config = load_processing_config()
    db_manager = DatabaseManager(config.database.path)
    detection_repo = DetectionRepository(db_manager)
    
    # Test the problematic query that caused the 500 error
    from datetime import datetime, timedelta
    start_time = (datetime.now() - timedelta(hours=24)).isoformat() + "Z"
    end_time = datetime.now().isoformat() + "Z"
    
    results = detection_repo.get_recent_filtered_with_thumbnails(
        start=start_time, end=end_time, limit=50
    )
    
    print(f"✅ Database query test passed - found {len(results)} detections")
    sys.exit(0)
    
except Exception as e:
    print(f"❌ Database query test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
''']
    results.append(run_command(db_test_cmd, "Real Database Query Test"))
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUITE SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 ALL TESTS PASSED ({passed}/{total})")
        print("✅ System is ready for deployment!")
        return 0
    else:
        print(f"❌ SOME TESTS FAILED ({passed}/{total} passed)")
        print("🔧 Please fix the failing tests before deployment")
        return 1


if __name__ == '__main__':
    sys.exit(main())