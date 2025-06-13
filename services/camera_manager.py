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
        self.dual_mode = self.camera_type in ("both", "dual", "usb+pi")
        self.cap: Optional[cv2.VideoCapture] = None
        self.picam2: Optional[Picamera2] = None
        self._initialize_camera()

    def _initialize_camera(self):
        if self.dual_mode:
            if Picamera2:
                try:
                    self.picam2 = Picamera2()
                    video_config = self.picam2.create_video_configuration(
                        main={"size": self.config.resolution, "format": "BGR888"},
                        controls={"FrameRate": self.config.fps},
                    )
                    self.picam2.configure(video_config)
                    self.picam2.start()
                except Exception as e:
                    print(f"Picamera2 init failed in dual mode: {e}")
                    self.picam2 = None

            self.cap = cv2.VideoCapture(self.config.device_index)
            if self.cap.isOpened():
                self._configure_camera()
            else:
                print(f"USB camera index {self.config.device_index} failed in dual mode")

            if not (self.cap and self.cap.isOpened()) and not self.picam2:
                raise RuntimeError("Failed to initialize cameras in dual mode")
            return

        if self.camera_type == "picamera2" and Picamera2:
            try:
                self.picam2 = Picamera2()
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
        if self.cap:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.resolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.resolution[1])
            self.cap.set(cv2.CAP_PROP_FPS, self.config.fps)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, self.config.buffer_size)

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        if self.dual_mode:
            ret_usb, usb_frame = (False, None)
            ret_pi, pi_frame = (False, None)
            if self.cap and self.cap.isOpened():
                ret_usb, usb_frame = self.cap.read()
            if self.picam2:
                try:
                    pi_frame = self.picam2.capture_array()
                    ret_pi = True
                except Exception:
                    ret_pi = False

            if not ret_usb or not ret_pi:
                return False, None

            if usb_frame is None or pi_frame is None:
                return False, None

            if usb_frame.shape[:2] != pi_frame.shape[:2]:
                pi_frame = cv2.resize(pi_frame, (usb_frame.shape[1], usb_frame.shape[0]))

            combined = np.hstack((usb_frame, pi_frame))
            return True, combined

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
        if self.dual_mode:
            usb_ok = self.cap is not None and self.cap.isOpened()
            pi_ok = self.picam2 is not None
            return usb_ok and pi_ok
        if self.camera_type == "picamera2":
            return self.picam2 is not None
        return self.cap is not None and self.cap.isOpened()

    def release(self):
        if self.dual_mode:
            if self.picam2:
                try:
                    self.picam2.close()
                except Exception:
                    pass
                self.picam2 = None
            if self.cap:
                self.cap.release()
            return
        if self.camera_type == "picamera2" and self.picam2:
            try:
                self.picam2.close()
            except Exception:
                pass
            self.picam2 = None
        if self.cap:
            self.cap.release()
            self.cap = None
