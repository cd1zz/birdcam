# BirdCam Test Harness

This directory contains integration tests and visual test harnesses for the BirdCam system components.

## Test Files

### 1. `test_auth_integration.py`
Integration tests for the authentication service using a real SQLite database.

**Tests:**
- User creation and duplicate prevention
- Authentication with correct/incorrect passwords
- JWT token generation and validation
- Token refresh functionality
- Password updates
- Role management and last admin protection
- User deactivation

**Run with:**
```bash
python tests/test_harness/test_auth_integration.py
```

### 2. `test_motion_detection_visual.py`
Visual tests for the motion detection system that creates test frames and visualizations.

**Tests:**
- Motion detection with various scenarios (no motion, small/large objects)
- Motion region boundaries
- Sensitivity threshold testing
- Adaptive background learning
- Saves visualization images to `/tmp/motion_test_*.png`

**Run with:**
```bash
python tests/test_harness/test_motion_detection_visual.py
```

### 3. `test_config_validation.py`
Comprehensive configuration validation tests.

**Tests:**
- Environment variable parsing (bool, int, float, list)
- Camera configuration scenarios
- Motion box configuration
- Detection confidence settings
- Storage path overrides
- Edge cases and error handling

**Run with:**
```bash
python tests/test_harness/test_config_validation.py
```

## Running All Tests

To run the unit tests:
```bash
# Run specific test suites
./scripts/run-tests.sh

# Or run individual test files
pytest tests/test_auth_service.py -v
pytest tests/test_config_settings.py -v
pytest tests/test_motion_detector.py -v
pytest tests/test_email_config.py -v
pytest tests/test_utils_auth.py -v
```

To run integration tests:
```bash
# Auth integration
python tests/test_harness/test_auth_integration.py

# Motion detection visual tests
python tests/test_harness/test_motion_detection_visual.py

# Configuration validation
python tests/test_harness/test_config_validation.py
```

## Test Coverage

The tests cover:

1. **Authentication Service**
   - User management (CRUD operations)
   - Password hashing and verification
   - JWT token creation and validation
   - Role-based access control
   - Security features (last admin protection)

2. **Configuration System**
   - Environment variable parsing
   - Multi-camera configuration
   - Motion detection settings
   - Storage path management
   - Email configuration

3. **Motion Detection**
   - Frame-based motion detection
   - Configurable motion regions
   - Sensitivity thresholds
   - Background subtraction
   - Contour analysis

## Requirements

- Python 3.8+
- All BirdCam dependencies installed
- OpenCV (cv2) for motion detection tests
- Write access to `/tmp/` for visual test outputs

## Notes

- The integration tests create temporary databases that are cleaned up automatically
- Visual tests save images to `/tmp/` for inspection
- All tests are designed to run without requiring the full BirdCam system to be running
- Mock objects are used where appropriate to isolate components