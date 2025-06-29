# services/camera_manager.py
import cv2
import numpy as np
from typing import Optional, Tuple, List, Dict, TYPE_CHECKING

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
            print(f"Picamera2 detection failed: {e}")

    return cameras


def print_detected_cameras(max_devices: int = 4) -> List[Dict[str, str]]:
    """Print detected cameras and return the list."""
    cams = detect_available_cameras(max_devices)
    if not cams:
        print("❌ No cameras detected")
    else:
        print(f"✅ Found {len(cams)} camera(s):")
        for cam in cams:
            pretty = "CSI" if cam["type"] == "picamera2" else "OpenCV"
            print(f" - ID {cam['id']} ({pretty})")
    return cams

class CameraManager:
    """Simplified camera manager that always uses Picamera2."""

    def __init__(self, config: 'CaptureConfig'):
        self.config = config
        self.picam2: Optional[Picamera2] = None
        self._initialize_camera()

    def _initialize_camera(self) -> None:
        """Initialize Picamera2 using the provided configuration."""
        if not Picamera2:
            raise RuntimeError("Picamera2 library not available")

        try:
            self.picam2 = Picamera2(camera_num=self.config.camera_id)
            video_config = self.picam2.create_video_configuration(
                main={"size": self.config.resolution}
            )
            self.picam2.configure(video_config)
            self.picam2.start()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Picamera2: {e}")

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        if not self.picam2:
            return False, None
        try:
            frame = self.picam2.capture_array()
            # Picamera2 returns RGB; convert to BGR for OpenCV processing
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            return True, frame
        except Exception:
            return False, None

    def is_opened(self) -> bool:
        return self.picam2 is not None

    def release(self) -> None:
        if self.picam2:
            try:
                self.picam2.close()
            except Exception:
                pass
            self.picam2 = None
