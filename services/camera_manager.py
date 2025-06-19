# services/camera_manager.py
import cv2
import numpy as np
from typing import Optional, Tuple
from config.settings import CaptureConfig

try:
    from picamera2 import Picamera2
except ImportError:  # pragma: no cover - picamera2 may not be installed
    Picamera2 = None

class CameraManager:
    def __init__(self, config: CaptureConfig):
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
                    main={"size": self.config.resolution, "format": "BGR888"},
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
