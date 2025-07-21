# services/camera_manager.py
import cv2
import numpy as np
from typing import Optional, Tuple, List, Dict, TYPE_CHECKING
from utils.capture_logger import logger

if TYPE_CHECKING:  # Avoid circular import at runtime
    from config.settings import CaptureConfig

try:
    from picamera2 import Picamera2
except ImportError:  # pragma: no cover - picamera2 may not be installed
    Picamera2 = None


def detect_available_cameras(max_devices: int = 4) -> List[Dict[str, str]]:
    """Detect connected cameras and return their IDs."""
    cameras: List[Dict[str, str]] = []

    if Picamera2:
        try:
            infos = Picamera2.global_camera_info()
            for idx, _ in enumerate(infos):
                cameras.append({"id": str(idx), "type": "picamera2"})
        except Exception as e:  # pragma: no cover - hardware specific
            logger.error(f"Picamera2 detection failed: {e}")

    # Also check for USB/OpenCV cameras
    for i in range(max_devices):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, _ = cap.read()
            cap.release()
            if ret:
                # Check if this is already detected as picamera2
                if not any(cam["id"] == str(i) and cam["type"] == "picamera2" for cam in cameras):
                    cameras.append({"id": str(i), "type": "opencv"})

    return cameras


def print_detected_cameras(max_devices: int = 4) -> List[Dict[str, str]]:
    """Print detected cameras and return the list."""
    cams = detect_available_cameras(max_devices)
    if not cams:
        logger.error("No cameras detected")
    else:
        logger.ok(f"Found {len(cams)} camera(s)")
        for cam in cams:
            pretty = "CSI" if cam["type"] == "picamera2" else "OpenCV"
            logger.camera(f"ID {cam['id']} ({pretty})")
    return cams

class CameraManager:
    """Camera manager that supports both Picamera2 and OpenCV cameras."""

    def __init__(self, config: 'CaptureConfig', force_opencv: bool = False):
        self.config = config
        self.picam2: Optional[Picamera2] = None
        self.cv_cap: Optional[cv2.VideoCapture] = None
        self.camera_type: Optional[str] = None
        self.force_opencv = force_opencv
        self._initialize_camera()

    def _initialize_camera(self) -> None:
        """Initialize camera using configured type or auto-detect."""
        camera_id = self.config.camera_id
        camera_type = self.config.camera_type  # Get type from config
        
        # Handle configured camera type
        if camera_type == 'opencv' or self.force_opencv:
            # Force OpenCV
            self._initialize_opencv()
            return
        elif camera_type == 'picamera2':
            # Force Picamera2
            if not Picamera2:
                raise RuntimeError("Picamera2 requested but not available")
            self._initialize_picamera2()
            return
        
        # Auto mode - try Picamera2 first
        if Picamera2:
            try:
                # Check if this camera ID is available in Picamera2
                infos = Picamera2.global_camera_info()
                if camera_id < len(infos):
                    # Check if it's a USB camera - if so, skip Picamera2
                    camera_info = infos[camera_id]
                    is_usb = "usb" in camera_info.get("Id", "").lower()
                    if not is_usb:
                        self.picam2 = Picamera2(camera_num=camera_id)
                        video_config = self.picam2.create_video_configuration(
                            main={"size": self.config.resolution}
                        )
                        self.picam2.configure(video_config)
                        self.picam2.start()
                        self.camera_type = "picamera2"
                        logger.info(f"Initialized Picamera2 for camera {camera_id}")
                        return
                    else:
                        logger.info(f"Camera {camera_id} is USB, skipping Picamera2")
            except Exception as e:
                logger.warning(f"Picamera2 init failed for camera {camera_id}: {e}")
                if self.picam2:
                    try:
                        self.picam2.close()
                    except:
                        pass
                    self.picam2 = None
        
        # Fall back to OpenCV
        self._initialize_opencv()
    
    def _initialize_picamera2(self) -> None:
        """Initialize Picamera2 camera."""
        try:
            infos = Picamera2.global_camera_info()
            if self.config.camera_id < len(infos):
                # Check if it's a USB camera - if so, fail
                camera_info = infos[self.config.camera_id]
                is_usb = "usb" in camera_info.get("Id", "").lower()
                if is_usb:
                    raise RuntimeError(f"Camera {self.config.camera_id} is USB, cannot use Picamera2")
                
                self.picam2 = Picamera2(camera_num=self.config.camera_id)
                video_config = self.picam2.create_video_configuration(
                    main={"size": self.config.resolution}
                )
                self.picam2.configure(video_config)
                self.picam2.start()
                self.camera_type = "picamera2"
                logger.info(f"Initialized Picamera2 for camera {self.config.camera_id}")
            else:
                raise RuntimeError(f"Camera {self.config.camera_id} not found in Picamera2")
        except Exception as e:
            if self.picam2:
                try:
                    self.picam2.close()
                except:
                    pass
                self.picam2 = None
            raise RuntimeError(f"Failed to initialize Picamera2: {e}")
    
    def _initialize_opencv(self) -> None:
        """Initialize OpenCV camera."""
        try:
            # Use configured video device or auto-detect
            if self.config.video_device is not None:
                # Use explicitly configured device
                video_device = self.config.video_device
                logger.info(f"Using configured video device {video_device} for camera {self.config.camera_id}")
            else:
                # Auto-detect based on camera ID
                video_device = self.config.camera_id
                
            self.cv_cap = cv2.VideoCapture(video_device)
            if self.cv_cap.isOpened():
                # Set resolution
                self.cv_cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.resolution[0])
                self.cv_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.resolution[1])
                self.cv_cap.set(cv2.CAP_PROP_FPS, self.config.fps)
                self.camera_type = "opencv"
                logger.info(f"Initialized OpenCV for camera {self.config.camera_id}")
            else:
                raise RuntimeError(f"Failed to open camera {self.config.camera_id} with OpenCV")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize camera {self.config.camera_id}: {e}")

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        if self.camera_type == "picamera2" and self.picam2:
            try:
                frame = self.picam2.capture_array()
                # Picamera2 returns RGB; convert to BGR for OpenCV processing
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                return True, frame
            except Exception as e:
                logger.error(f"Picamera2 read error: {e}")
                # Try to recover by releasing and reinitializing
                self.release()
                try:
                    self._initialize_camera()
                    return False, None
                except Exception:
                    return False, None
        elif self.camera_type == "opencv" and self.cv_cap:
            try:
                ret, frame = self.cv_cap.read()
                return ret, frame if ret else None
            except Exception as e:
                logger.error(f"OpenCV read error: {e}")
                # Try to recover by releasing and reinitializing
                self.release()
                try:
                    self._initialize_camera()
                    return False, None
                except Exception:
                    return False, None
        return False, None

    def is_opened(self) -> bool:
        if self.camera_type == "picamera2":
            return self.picam2 is not None
        elif self.camera_type == "opencv":
            return self.cv_cap is not None and self.cv_cap.isOpened()
        return False

    def release(self) -> None:
        if self.picam2:
            try:
                self.picam2.close()
            except Exception as e:
                logger.error(f"Picamera2 release error: {e}")
            finally:
                self.picam2 = None
        if self.cv_cap:
            try:
                self.cv_cap.release()
            except Exception as e:
                logger.error(f"OpenCV release error: {e}")
            finally:
                self.cv_cap = None
        self.camera_type = None
