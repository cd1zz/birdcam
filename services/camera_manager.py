# services/camera_manager.py
import cv2
import numpy as np
from typing import Optional, Tuple
from config.settings import CaptureConfig

class CameraManager:
    def __init__(self, config: CaptureConfig):
        self.config = config
        self.cap: Optional[cv2.VideoCapture] = None
        self._initialize_camera()
    
    def _initialize_camera(self):
        # Try direct camera first
        self.cap = cv2.VideoCapture(0)
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
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.resolution[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.resolution[1])
        self.cap.set(cv2.CAP_PROP_FPS, self.config.fps)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, self.config.buffer_size)
    
    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        if not self.cap or not self.cap.isOpened():
            return False, None
        return self.cap.read()
    
    def is_opened(self) -> bool:
        return self.cap is not None and self.cap.isOpened()
    
    def release(self):
        if self.cap:
            self.cap.release()