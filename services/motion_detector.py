# services/motion_detector.py - FIXED VERSION
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
        """Enhanced motion detection with WORKING sensitivity threshold"""
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
        
        # FIXED: Apply sensitivity threshold from UI
        # Convert motion_threshold to a threshold value (invert it - lower number = more sensitive)
        sensitivity_threshold = max(1, int(10000 - self.config.threshold) // 40)  # Convert 1000-10000 to ~225-1
        
        # Apply threshold to the foreground mask
        _, fg_mask_thresh = cv2.threshold(fg_mask, sensitivity_threshold, 255, cv2.THRESH_BINARY)
        
        # Count total white pixels (motion pixels)
        motion_pixel_count = cv2.countNonZero(fg_mask_thresh)
        
        # OPTION 1: Use pixel count method (more direct sensitivity control)
        if motion_pixel_count > self.config.min_contour_area:
            return True
        
        # OPTION 2: Use contour method (better for object detection)
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
        
        # Count pixels and contours
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
            'motion_detected': motion_pixel_count > self.config.min_contour_area or largest_contour_area > self.config.min_contour_area
        }