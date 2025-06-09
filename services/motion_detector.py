# services/motion_detector.py
import cv2
import numpy as np
from typing import Optional, Tuple
from core.models import MotionRegion
from config.settings import MotionConfig

class MotionDetector:
    def __init__(self, config: MotionConfig):
        self.config = config
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2(
            detectShadows=False, 
            varThreshold=16, 
            history=500
        )
        self.motion_region: Optional[MotionRegion] = None
        if config.region:
            self.motion_region = MotionRegion(*config.region)
    
    def set_motion_region(self, region: MotionRegion):
        self.motion_region = region
    
    def detect_motion(self, frame: np.ndarray) -> bool:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Set default region if none specified
        if self.motion_region is None:
            h, w = gray.shape
            self.motion_region = MotionRegion(
                int(w * 0.2), int(h * 0.2),
                int(w * 0.8), int(h * 0.8)
            )
        
        # Create mask for region of interest
        mask = np.zeros(gray.shape, dtype=np.uint8)
        mask[self.motion_region.y1:self.motion_region.y2, 
             self.motion_region.x1:self.motion_region.x2] = 255
        
        # Apply background subtraction
        fg_mask = self.background_subtractor.apply(gray, learningRate=self.config.learning_rate)
        fg_mask = cv2.bitwise_and(fg_mask, mask)
        
        # Find significant contours
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            if cv2.contourArea(contour) > self.config.min_contour_area:
                return True
        
        return False
