# services/motion_event_broadcaster.py
import threading
import time
from typing import Dict, Set, Callable, Optional
from dataclasses import dataclass
from datetime import datetime
from utils.capture_logger import logger


@dataclass
class MotionEvent:
    """Represents a motion detection event"""
    camera_id: int
    timestamp: float
    confidence: float = 1.0
    location: Optional[tuple] = None  # (x, y) center of motion


class MotionEventBroadcaster:
    """
    Central motion event broadcaster that coordinates motion detection across cameras.
    When motion is detected on one camera, it can trigger recording on all cameras.
    """
    
    def __init__(self, cross_trigger_enabled: bool = True, trigger_timeout: float = 5.0):
        """
        Initialize the motion event broadcaster.
        
        Args:
            cross_trigger_enabled: Whether to enable cross-camera triggering
            trigger_timeout: Time in seconds to keep triggering after motion stops
        """
        self.cross_trigger_enabled = cross_trigger_enabled
        self.trigger_timeout = trigger_timeout
        
        # Thread-safe storage for motion events and listeners
        self._lock = threading.Lock()
        self._motion_listeners: Dict[int, Callable[[MotionEvent], None]] = {}
        self._recent_motion_events: Dict[int, MotionEvent] = {}
        
        # Cross-camera trigger state
        self._global_motion_active = False
        self._last_motion_time = 0.0
        
        # Statistics
        self._total_events = 0
        self._cross_triggers = 0
        
        logger.motion("MotionEventBroadcaster initialized")
        logger.config(f"Cross-camera triggering: {'enabled' if cross_trigger_enabled else 'disabled'}")
        logger.config(f"Trigger timeout: {trigger_timeout}s")
    
    def register_camera(self, camera_id: int, motion_callback: Callable[[MotionEvent], None]):
        """
        Register a camera with the broadcaster.
        
        Args:
            camera_id: Unique identifier for the camera
            motion_callback: Function to call when motion should be triggered on this camera
        """
        with self._lock:
            self._motion_listeners[camera_id] = motion_callback
            logger.camera(f"Camera {camera_id} registered with motion broadcaster")
    
    def unregister_camera(self, camera_id: int):
        """Unregister a camera from the broadcaster"""
        with self._lock:
            if camera_id in self._motion_listeners:
                del self._motion_listeners[camera_id]
                logger.camera(f"Camera {camera_id} unregistered from motion broadcaster")
            
            if camera_id in self._recent_motion_events:
                del self._recent_motion_events[camera_id]
    
    def report_motion(self, camera_id: int, confidence: float = 1.0, location: Optional[tuple] = None):
        """
        Report motion detection from a camera.
        
        Args:
            camera_id: ID of the camera that detected motion
            confidence: Confidence level of the motion detection (0.0 to 1.0)
            location: Optional (x, y) center of motion
        """
        current_time = time.time()
        
        # Create motion event
        event = MotionEvent(
            camera_id=camera_id,
            timestamp=current_time,
            confidence=confidence,
            location=location
        )
        
        with self._lock:
            # Update statistics
            self._total_events += 1
            self._recent_motion_events[camera_id] = event
            
            # Update global motion state
            was_global_motion = self._global_motion_active
            self._global_motion_active = True
            self._last_motion_time = current_time
            
            # Log the motion event
            logger.motion(f"Motion detected on camera {camera_id}", confidence=f"{confidence:.2f}")
            
            # Trigger recording based on cross-trigger settings
            triggered_cameras = []
            
            for listener_camera_id, callback in self._motion_listeners.items():
                # Always trigger the detecting camera itself
                # Only trigger other cameras if cross-triggering is enabled
                if listener_camera_id == camera_id or self.cross_trigger_enabled:
                    try:
                        callback(event)
                        triggered_cameras.append(listener_camera_id)
                        
                        # Count cross-triggers (triggers to cameras other than the detecting camera)
                        if listener_camera_id != camera_id:
                            self._cross_triggers += 1
                            
                    except Exception as e:
                        logger.error(f"Error triggering camera {listener_camera_id}: {e}")
            
            if triggered_cameras:
                logger.trigger(f"Triggered recording on cameras: {triggered_cameras}")
    
    def is_motion_active(self) -> bool:
        """Check if motion is currently active (within timeout period)"""
        current_time = time.time()
        
        with self._lock:
            if not self._global_motion_active:
                return False
            
            # Check if we're still within the timeout period
            time_since_motion = current_time - self._last_motion_time
            if time_since_motion > self.trigger_timeout:
                self._global_motion_active = False
                return False
            
            return True
    
    def get_active_cameras(self) -> Set[int]:
        """Get set of cameras that recently detected motion"""
        current_time = time.time()
        active_cameras = set()
        
        with self._lock:
            for camera_id, event in self._recent_motion_events.items():
                if current_time - event.timestamp <= self.trigger_timeout:
                    active_cameras.add(camera_id)
        
        return active_cameras
    
    def get_statistics(self) -> Dict:
        """Get motion detection statistics"""
        with self._lock:
            # Calculate active cameras directly to avoid deadlock
            current_time = time.time()
            active_cameras_count = 0
            for camera_id, event in self._recent_motion_events.items():
                if current_time - event.timestamp <= self.trigger_timeout:
                    active_cameras_count += 1
            
            return {
                'total_events': self._total_events,
                'cross_triggers': self._cross_triggers,
                'registered_cameras': len(self._motion_listeners),
                'active_cameras': active_cameras_count,
                'global_motion_active': self._global_motion_active,
                'last_motion_time': self._last_motion_time
            }
    
    def set_cross_trigger_enabled(self, enabled: bool):
        """Enable or disable cross-camera triggering"""
        with self._lock:
            self.cross_trigger_enabled = enabled
            logger.config(f"Cross-camera triggering {'enabled' if enabled else 'disabled'}")
    
    def set_trigger_timeout(self, timeout: float):
        """Set the trigger timeout duration"""
        with self._lock:
            self.trigger_timeout = timeout
            logger.config(f"Trigger timeout set to {timeout}s")
    
    def clear_motion_state(self):
        """Clear all motion state (useful for testing)"""
        with self._lock:
            self._global_motion_active = False
            self._last_motion_time = 0.0
            self._recent_motion_events.clear()
            logger.info("Motion state cleared")


# Global instance for the motion broadcaster
_motion_broadcaster: Optional[MotionEventBroadcaster] = None


def get_motion_broadcaster() -> MotionEventBroadcaster:
    """Get the global motion broadcaster instance"""
    global _motion_broadcaster
    if _motion_broadcaster is None:
        _motion_broadcaster = MotionEventBroadcaster()
    return _motion_broadcaster


def initialize_motion_broadcaster(cross_trigger_enabled: bool = True, trigger_timeout: float = 5.0):
    """Initialize the global motion broadcaster with custom settings"""
    global _motion_broadcaster
    _motion_broadcaster = MotionEventBroadcaster(cross_trigger_enabled, trigger_timeout)
    return _motion_broadcaster