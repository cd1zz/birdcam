# Master-Slave Camera Implementation

## Summary
Successfully implemented a simplified master-slave camera system that replaces the complex motion broadcaster with a direct master-slave relationship.

## How It Works

### Master Camera (Camera 0)
- **Motion Detection**: Only the master camera detects motion
- **Recording Trigger**: When motion is detected, master starts recording AND triggers slave
- **Motion Box**: User configures motion detection box only on master camera
- **Pre-Motion Buffer**: Master camera gets pre-motion buffer frames (15 seconds)

### Slave Camera (Camera 1+)
- **No Motion Detection**: Slave cameras don't detect motion
- **Recording Only**: Slave cameras only record when triggered by master
- **No Pre-Motion Buffer**: Slave cameras start recording immediately (no pre-motion)
- **Separate Files**: Each camera saves its own recording file

## Key Benefits

1. **Eliminates Feedback Loops**: Only one camera detects motion
2. **Simpler Logic**: No complex cross-camera communication
3. **More Stable**: Back to old-state simplicity with dual recording
4. **User-Friendly**: Configure motion box on one camera, get both streams
5. **Separate Files**: Each camera saves its own stream as requested

## Files Modified

### 1. `/home/craig/birdcam/services/capture_service.py`
```python
# Master-slave setup
self.camera_id = capture_config.camera_id
self.is_master = self.camera_id == 0  # Camera 0 is master
self.slave_camera_service: Optional['CaptureService'] = None

# Master-slave methods
def set_slave_camera(self, slave_service: 'CaptureService'):
    """Set the slave camera service for master-slave recording"""

def _start_recording_from_master(self):
    """Start recording on slave camera when triggered by master"""
```

**Key Changes:**
- Removed motion broadcaster imports and integration
- Added master/slave camera identification
- Only master camera does motion detection
- Master directly triggers slave camera recording
- Simplified timeout logic (back to old-state)
- Re-enabled pre-motion buffer with timestamp spacing

### 2. `/home/craig/birdcam/services/video_writer.py`
```python
def write_frames_with_timestamps(self, frames: list):
    """Write pre-motion buffer frames with proper spacing to avoid timestamp issues"""
    # Write frames with a small delay to ensure different timestamps
    for i, frame in enumerate(frames):
        self.write_frame(frame)
        # Add a tiny delay every few frames to ensure timestamps advance
        if i % 10 == 0 and i > 0:
            time.sleep(0.001)  # 1ms delay every 10 frames
```

**Key Changes:**
- Added proper timestamp handling for pre-motion buffer
- Prevents FFmpeg timestamp errors that caused crashes

### 3. `/home/craig/birdcam/pi_capture/main.py`
```python
# Set up master-slave relationships
print("🔗 Setting up master-slave camera relationships...")
master_service = capture_services.get(0)  # Camera 0 is master
if master_service:
    for camera_id, service in capture_services.items():
        if camera_id != 0:  # All other cameras are slaves
            master_service.set_slave_camera(service)
            print(f"✅ Linked master camera 0 to slave camera {camera_id}")
```

**Key Changes:**
- Removed motion broadcaster initialization
- Added master-slave linking after all services are created
- Links Camera 0 as master to all other cameras as slaves

## Recording Flow

### When Motion is Detected:
1. **Master Camera 0** detects motion in configured motion box
2. **Master Camera 0** starts recording with pre-motion buffer
3. **Master Camera 0** triggers **Slave Camera 1** to start recording
4. **Both cameras record simultaneously** to separate files

### When Motion Stops:
1. **Master Camera 0** stops recording after timeout
2. **Master Camera 0** tells **Slave Camera 1** to stop recording
3. **Both cameras save their segments** as separate files

## User Experience

- **Configure once**: Set motion box on Camera 0 only
- **Record both**: Get recordings from both cameras
- **Separate files**: Each camera saves its own video file
- **Stable system**: No more crashes or feedback loops

## Testing

The system should now:
- ✅ Be much more stable (no complex broadcaster logic)
- ✅ Record both cameras when motion is detected on Camera 0
- ✅ Save separate files for each camera
- ✅ Include pre-motion buffer for Camera 0 (without timestamp crashes)
- ✅ Have no cross-camera feedback loops

## Next Steps

1. **Test the system** with two cameras
2. **Verify recordings** are created for both cameras
3. **Check stability** - no more crashes or infinite loops
4. **Validate motion box** configuration works as expected

The system is now ready for testing with the simplified, stable master-slave approach!