# Terminology Update Summary

## Overview
Successfully updated all terminology from "master/slave" to "active/passive" across the entire codebase and documentation.

## Files Modified

### Code Files
1. **`services/capture_service.py`**
   - `self.is_master` → `self.is_active`
   - `self.slave_camera_service` → `self.passive_camera_service`
   - `set_slave_camera()` → `set_passive_camera()`
   - `_start_recording_from_master()` → `_start_recording_from_active()`
   - Updated all comments and log messages

2. **`pi_capture/main.py`**
   - `master_service` → `active_service`
   - `set_slave_camera()` → `set_passive_camera()`
   - Updated setup messages and comments

### Documentation Files
1. **`MASTER_SLAVE_IMPLEMENTATION.md`** → **`ACTIVE_PASSIVE_IMPLEMENTATION.md`**
   - Renamed file completely
   - Updated all references throughout document
   - Changed title and all section headers

2. **`VIDEO_RECORDING_BUG_ANALYSIS.md`**
   - Added section about new active-passive implementation
   - Updated to reflect current architecture

3. **`CROSS_CAMERA_MOTION.md`**
   - Marked as DEPRECATED
   - Added warning about replacement with active-passive system
   - Explained why the old system was replaced
   - Added migration information

## Terminology Changes

| Old Term | New Term | Description |
|----------|----------|-------------|
| Master Camera | Active Camera | Camera that detects motion |
| Slave Camera | Passive Camera | Camera that records when triggered |
| Master-Slave | Active-Passive | System architecture description |
| set_slave_camera() | set_passive_camera() | Method to link cameras |
| _start_recording_from_master() | _start_recording_from_active() | Method to trigger recording |
| is_master | is_active | Boolean flag for camera role |
| slave_camera_service | passive_camera_service | Reference to dependent camera |

## System Architecture (Updated)

### Active Camera (Camera 0)
- **Role**: Detects motion using configured motion box
- **Responsibilities**: 
  - Motion detection
  - Recording with pre-motion buffer
  - Triggering passive cameras
  - Stopping all cameras when motion timeout reached

### Passive Camera (Camera 1+)
- **Role**: Records when triggered by active camera
- **Responsibilities**:
  - Recording without motion detection
  - No pre-motion buffer
  - Responds to active camera triggers
  - Saves separate video files

## Benefits of New Terminology

1. **More Inclusive**: Avoids problematic master/slave terminology
2. **More Accurate**: Better describes the actual relationship
3. **Clear Roles**: Active = does something, Passive = responds
4. **Industry Standard**: Aligns with modern technical terminology

## User Impact

- **No functional changes**: System works exactly the same
- **Same configuration**: Motion box still configured on Camera 0
- **Same behavior**: Camera 0 detects motion, all cameras record
- **Same files**: Separate video files for each camera
- **Improved stability**: Still uses simplified architecture

## Verification

All terminology has been updated consistently across:
- ✅ Source code files
- ✅ Documentation files
- ✅ Comments and log messages
- ✅ Variable names and method names
- ✅ File names

No remaining references to master/slave terminology found in the codebase.

## Next Steps

The system is ready for testing with the new active-passive terminology. All functionality remains the same, but now uses more appropriate and inclusive language throughout.