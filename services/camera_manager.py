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
    """Detect connected cameras and return their IDs and types."""
    cameras: List[Dict[str, str]] = []

    if Picamera2:
        try:
            infos = Picamera2.global_camera_info()
            for idx, _ in enumerate(infos):
                cameras.append({"id": str(idx), "type": "picamera2"})
        except Exception as e:  # pragma: no cover - hardware specific
            print(f"Picamera2 detection failed: {e}")

    for i in range(max_devices):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            cameras.append({"id": str(i), "type": "opencv"})
            cap.release()

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
    def __init__(self, config: 'CaptureConfig'):
        self.config = config
        self.camera_type = config.camera_type.lower()
        self.cap: Optional[cv2.VideoCapture] = None
        self.picam2: Optional[Picamera2] = None
        self._initialize_camera()

    def _initialize_camera(self):
        if self.camera_type == "picamera2" and Picamera2:
            try:
                self.picam2 = Picamera2(camera_num=self.config.camera_id)
                video_config = self.picam2.create_video_configuration(
                    main={"size": self.config.resolution},
                    controls={"FrameRate": self.config.fps},
                )
                self.picam2.configure(video_config)
                self.picam2.start()
                return
            except Exception as e:
                print(f"Picamera2 init failed: {e}, falling back to OpenCV")
                self.picam2 = None
                self.camera_type = "opencv"

        # Try direct camera first via OpenCV
        self.cap = cv2.VideoCapture(self.config.camera_id)
        if self.cap.isOpened():
            self._configure_camera()
            return

        # Fallback to RTSP
        self.cap = cv2.VideoCapture(self.config.stream_url, cv2.CAP_FFMPEG)
        if self.cap.isOpened():
            self._configure_camera()
            return

        raise RuntimeError("Failed to initialize camera")

    def _configure_camera(self):
        if self.cap:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.resolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.resolution[1])
            self.cap.set(cv2.CAP_PROP_FPS, self.config.fps)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, self.config.buffer_size)

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        if self.camera_type == "picamera2" and self.picam2:
            try:
                frame = self.picam2.capture_array()
                # Picamera2 returns RGB even when BGR is requested.
                # Convert to BGR so OpenCV processing works correctly.
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                return True, frame
            except Exception:
                return False, None

        if not self.cap or not self.cap.isOpened():
            return False, None
        return self.cap.read()

    def is_opened(self) -> bool:
        if self.camera_type == "picamera2":
            return self.picam2 is not None
        return self.cap is not None and self.cap.isOpened()

    def release(self):
        if self.camera_type == "picamera2" and self.picam2:
            try:
                self.picam2.close()
            except Exception:
                pass
            self.picam2 = None
        if self.cap:
            self.cap.release()
