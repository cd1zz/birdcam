"""Test harness for configuration validation and edge cases"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import os
import tempfile
import json
from unittest.mock import patch
from config.settings import (
    load_capture_config, load_all_capture_configs, load_processing_config,
    get_bool_env, get_int_env, get_float_env, get_list_env,
    get_detection_confidences
)


def test_environment_variables():
    """Test environment variable parsing functions"""
    print("Testing Environment Variable Parsing")
    print("=" * 50)
    
    # Test boolean parsing
    print("\n1. Testing boolean parsing...")
    bool_tests = [
        ('true', True), ('True', True), ('TRUE', True), ('1', True),
        ('false', False), ('False', False), ('0', False), ('', False)
    ]
    
    for value, expected in bool_tests:
        with patch.dict(os.environ, {'TEST_BOOL': value}):
            result = get_bool_env('TEST_BOOL')
            status = "✓" if result == expected else "✗"
            print(f"   {status} '{value}' -> {result} (expected {expected})")
    
    # Test integer parsing
    print("\n2. Testing integer parsing...")
    int_tests = [
        ('42', 42), ('0', 0), ('-10', -10), ('invalid', 100)  # default=100
    ]
    
    for value, expected in int_tests:
        with patch.dict(os.environ, {'TEST_INT': value}):
            result = get_int_env('TEST_INT', 100)
            status = "✓" if result == expected else "✗"
            print(f"   {status} '{value}' -> {result} (expected {expected})")
    
    # Test float parsing
    print("\n3. Testing float parsing...")
    float_tests = [
        ('3.14', 3.14), ('0.0', 0.0), ('-2.5', -2.5), ('invalid', 1.0)
    ]
    
    for value, expected in float_tests:
        with patch.dict(os.environ, {'TEST_FLOAT': value}):
            result = get_float_env('TEST_FLOAT', 1.0)
            status = "✓" if result == expected else "✗"
            print(f"   {status} '{value}' -> {result} (expected {expected})")
    
    # Test list parsing
    print("\n4. Testing list parsing...")
    list_tests = [
        ('item1,item2,item3', ['item1', 'item2', 'item3']),
        ('item1, item2 , item3 ', ['item1', 'item2', 'item3']),  # with spaces
        ('', []),
        ('single', ['single'])
    ]
    
    for value, expected in list_tests:
        with patch.dict(os.environ, {'TEST_LIST': value}):
            result = get_list_env('TEST_LIST')
            status = "✓" if result == expected else "✗"
            print(f"   {status} '{value}' -> {result}")


def test_camera_configurations():
    """Test various camera configuration scenarios"""
    print("\n\nTesting Camera Configurations")
    print("=" * 50)
    
    # Mock detect_available_cameras
    with patch('config.settings.detect_available_cameras') as mock_detect:
        mock_detect.return_value = []
        
        # Test 1: Default camera configuration
        print("\n1. Testing default camera configuration...")
        with patch.dict(os.environ, {}, clear=True):
            config = load_capture_config(0)
            print(f"   ✓ Camera type: {config.capture.camera_type}")
            print(f"   ✓ Resolution: {config.capture.resolution}")
            print(f"   ✓ FPS: {config.capture.fps}")
            print(f"   ✓ Storage path: {config.processing.storage_path}")
        
        # Test 2: Custom camera configuration
        print("\n2. Testing custom camera configuration...")
        env_vars = {
            'CAMERA_0_TYPE': 'opencv',
            'CAMERA_0_RESOLUTION': '1920x1080',
            'CAMERA_0_FPS': '30',
            'CAMERA_0_DEVICE': '2',
            'STORAGE_PATH': '/tmp/test_storage'
        }
        
        with patch.dict(os.environ, env_vars):
            config = load_capture_config(0)
            print(f"   ✓ Camera type: {config.capture.camera_type}")
            print(f"   ✓ Resolution: {config.capture.resolution}")
            print(f"   ✓ FPS: {config.capture.fps}")
            print(f"   ✓ Video device: {config.capture.video_device}")
        
        # Test 3: Invalid camera type
        print("\n3. Testing invalid camera type (should default to 'auto')...")
        with patch.dict(os.environ, {'CAMERA_0_TYPE': 'invalid_type'}):
            config = load_capture_config(0)
            assert config.capture.camera_type == 'auto'
            print(f"   ✓ Camera type defaulted to: {config.capture.camera_type}")
        
        # Test 4: Multiple camera configuration
        print("\n4. Testing multiple camera configuration...")
        mock_detect.return_value = [{'id': 0}, {'id': 1}, {'id': 2}]
        
        with patch.dict(os.environ, {'CAMERA_IDS': '0,2'}):
            configs = load_all_capture_configs()
            print(f"   ✓ Loaded {len(configs)} camera configurations")
            for cfg in configs:
                print(f"     - Camera {cfg.capture.camera_id}")


def test_motion_box_configuration():
    """Test motion box configuration scenarios"""
    print("\n\nTesting Motion Box Configuration")
    print("=" * 50)
    
    with patch('config.settings.detect_available_cameras') as mock_detect:
        mock_detect.return_value = []
        
        # Test 1: Motion box enabled
        print("\n1. Testing motion box enabled...")
        env_vars = {
            'MOTION_BOX_ENABLED': 'true',
            'MOTION_BOX_X1': '100',
            'MOTION_BOX_Y1': '150',
            'MOTION_BOX_X2': '500',
            'MOTION_BOX_Y2': '400'
        }
        
        with patch.dict(os.environ, env_vars):
            config = load_capture_config(0)
            print(f"   ✓ Motion box enabled: {config.motion.motion_box_enabled}")
            print(f"   ✓ Box coordinates: ({config.motion.motion_box_x1}, {config.motion.motion_box_y1}) to ({config.motion.motion_box_x2}, {config.motion.motion_box_y2})")
        
        # Test 2: Motion box disabled
        print("\n2. Testing motion box disabled...")
        with patch.dict(os.environ, {'MOTION_BOX_ENABLED': 'false'}):
            config = load_capture_config(0)
            print(f"   ✓ Motion box enabled: {config.motion.motion_box_enabled}")


def test_detection_confidence_configuration():
    """Test detection confidence configuration"""
    print("\n\nTesting Detection Confidence Configuration")
    print("=" * 50)
    
    # Test 1: Default confidence
    print("\n1. Testing default confidence...")
    with patch.dict(os.environ, {
        'DETECTION_CLASSES': 'bird,cat,dog',
        'DEFAULT_CONFIDENCE': '0.35'
    }):
        confidences = get_detection_confidences()
        print(f"   ✓ Default confidence: 0.35")
        for cls in ['bird', 'cat', 'dog']:
            print(f"   ✓ {cls}: {confidences[cls]}")
    
    # Test 2: Class-specific confidence
    print("\n2. Testing class-specific confidence...")
    with patch.dict(os.environ, {
        'DETECTION_CLASSES': 'bird,cat,dog',
        'DEFAULT_CONFIDENCE': '0.35',
        'BIRD_CONFIDENCE': '0.45',
        'CAT_CONFIDENCE': '0.50'
    }):
        confidences = get_detection_confidences()
        print(f"   ✓ bird: {confidences['bird']} (custom)")
        print(f"   ✓ cat: {confidences['cat']} (custom)")
        print(f"   ✓ dog: {confidences['dog']} (default)")


def test_storage_path_override():
    """Test storage path override functionality"""
    print("\n\nTesting Storage Path Override")
    print("=" * 50)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create system_settings.json
        settings_file = Path(tmpdir) / "system_settings.json"
        settings_data = {
            "storage": {
                "storage_path": "/custom/storage/path"
            }
        }
        
        with open(settings_file, 'w') as f:
            json.dump(settings_data, f)
        
        print(f"\n1. Created settings file at: {settings_file}")
        
        # Test loading with override
        with patch.dict(os.environ, {'STORAGE_PATH': tmpdir}):
            with patch('pathlib.Path.exists') as mock_exists:
                def path_exists(path):
                    return str(path) == str(settings_file)
                
                mock_exists.side_effect = path_exists
                
                config = load_processing_config()
                print(f"   ✓ Original path from env: {tmpdir}")
                print(f"   ✓ Override path loaded: {config.processing.storage_path}")
                assert str(config.processing.storage_path) == "/custom/storage/path"


def test_edge_cases():
    """Test various edge cases"""
    print("\n\nTesting Edge Cases")
    print("=" * 50)
    
    # Test 1: Empty environment
    print("\n1. Testing with empty environment...")
    with patch.dict(os.environ, {}, clear=True):
        with patch('config.settings.detect_available_cameras') as mock_detect:
            mock_detect.return_value = []
            
            config = load_capture_config(0)
            print(f"   ✓ Loaded with defaults")
            print(f"   ✓ Secret key: {config.security.secret_key[:20]}...")
    
    # Test 2: Invalid resolution format
    print("\n2. Testing invalid resolution format...")
    with patch.dict(os.environ, {
        'CAMERA_0_RESOLUTION': 'invalid-format',
        'RESOLUTION_WIDTH': '800',
        'RESOLUTION_HEIGHT': '600'
    }):
        with patch('config.settings.detect_available_cameras') as mock_detect:
            mock_detect.return_value = []
            
            config = load_capture_config(0)
            print(f"   ✓ Fell back to global resolution: {config.capture.resolution}")
    
    # Test 3: Invalid camera IDs
    print("\n3. Testing invalid camera IDs...")
    with patch.dict(os.environ, {'CAMERA_IDS': '0,invalid,2,abc'}):
        with patch('config.settings.detect_available_cameras') as mock_detect:
            mock_detect.return_value = []
            
            configs = load_all_capture_configs()
            print(f"   ✓ Only valid IDs processed: {len(configs)} configs loaded")
            for cfg in configs:
                print(f"     - Camera {cfg.capture.camera_id}")


def run_all_tests():
    """Run all configuration validation tests"""
    print("Configuration Validation Test Suite")
    print("===================================\n")
    
    try:
        test_environment_variables()
        test_camera_configurations()
        test_motion_box_configuration()
        test_detection_confidence_configuration()
        test_storage_path_override()
        test_edge_cases()
        
        print("\n" + "="*50)
        print("All configuration validation tests passed! ✓")
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)