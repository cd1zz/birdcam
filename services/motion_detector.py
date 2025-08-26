# services/motion_detector.py
import cv2
import numpy as np
from typing import Optional
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
        elif config.motion_box_enabled:
            self.motion_region = MotionRegion(
                config.motion_box_x1, 
                config.motion_box_y1, 
                config.motion_box_x2, 
                config.motion_box_y2
            )
    
    def set_motion_region(self, region: MotionRegion):
        self.motion_region = region
    
    def detect_motion(self, frame: np.ndarray) -> bool:
        """Detect motion using contour area within the configured region"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Set default region if none specified and motion box is disabled
        if self.motion_region is None and not self.config.motion_box_enabled:
            h, w = gray.shape
            self.motion_region = MotionRegion(
                int(w * 0.2), int(h * 0.2),
                int(w * 0.8), int(h * 0.8)
            )
        elif self.motion_region is None and self.config.motion_box_enabled:
            # Use motion box coordinates from config
            self.motion_region = MotionRegion(
                self.config.motion_box_x1, 
                self.config.motion_box_y1, 
                self.config.motion_box_x2, 
                self.config.motion_box_y2
            )
        
        # Skip motion detection if motion box is disabled
        if not self.config.motion_box_enabled:
            return False
        
        # Create mask for region of interest
        mask = np.zeros(gray.shape, dtype=np.uint8)
        mask[self.motion_region.y1:self.motion_region.y2, 
             self.motion_region.x1:self.motion_region.x2] = 255
        
        # Apply background subtraction
        fg_mask = self.background_subtractor.apply(gray, learningRate=self.config.learning_rate)
        fg_mask = cv2.bitwise_and(fg_mask, mask)
        
        # Convert user threshold to a sensitivity value and apply binary threshold
        sensitivity_threshold = max(1, int(10000 - self.config.threshold) // 40)
        _, fg_mask_thresh = cv2.threshold(fg_mask, sensitivity_threshold, 255, cv2.THRESH_BINARY)

        # Find contours within the thresholded mask
        contours, _ = cv2.findContours(fg_mask_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            if cv2.contourArea(contour) > self.config.min_contour_area:
                return True
        
        return False
    
    def get_debug_info(self, frame: np.ndarray) -> dict:
        """Get debug information about motion detection"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if self.motion_region is None:
            return {'error': 'No motion region set'}
        
        # Create mask
        mask = np.zeros(gray.shape, dtype=np.uint8)
        mask[self.motion_region.y1:self.motion_region.y2, 
             self.motion_region.x1:self.motion_region.x2] = 255
        
        # Background subtraction
        fg_mask = self.background_subtractor.apply(gray, learningRate=self.config.learning_rate)
        fg_mask = cv2.bitwise_and(fg_mask, mask)
        
        # Apply threshold
        sensitivity_threshold = max(1, int(10000 - self.config.threshold) // 40)
        _, fg_mask_thresh = cv2.threshold(fg_mask, sensitivity_threshold, 255, cv2.THRESH_BINARY)
        
        # Count pixels and contours for debugging purposes
        motion_pixel_count = cv2.countNonZero(fg_mask_thresh)
        contours, _ = cv2.findContours(fg_mask_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        largest_contour_area = 0
        if contours:
            largest_contour_area = max([cv2.contourArea(c) for c in contours])
        
        return {
            'motion_pixels': motion_pixel_count,
            'contour_count': len(contours),
            'largest_contour': largest_contour_area,
            'sensitivity_threshold': sensitivity_threshold,
            'min_contour_area': self.config.min_contour_area,
            'motion_detected': largest_contour_area > self.config.min_contour_area
        }