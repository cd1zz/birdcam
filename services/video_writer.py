# services/video_writer.py
import cv2
from pathlib import Path
from typing import Optional
from core.models import CaptureSegment
from datetime import datetime
from typing import Tuple
import numpy as np

class VideoWriter:
    def __init__(self, output_dir: Path, fps: int = 10, resolution: Tuple[int, int] = (640, 480)):
        self.output_dir = output_dir
        self.fps = fps
        self.resolution = resolution
        self.writer: Optional[cv2.VideoWriter] = None
        self.current_segment: Optional[CaptureSegment] = None
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def start_segment(self, motion_triggered: bool = False) -> CaptureSegment:
        if self.writer:
            self.finish_segment()
        
        timestamp = datetime.now()
        filename = f"segment_{timestamp.strftime('%Y%m%d_%H%M%S')}.mp4"
        filepath = self.output_dir / filename
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.writer = cv2.VideoWriter(str(filepath), fourcc, self.fps, self.resolution)
        
        if not self.writer.isOpened():
            raise RuntimeError("Failed to initialize video writer")
        
        self.current_segment = CaptureSegment(
            filename=filename,
            start_time=timestamp,
            has_motion=motion_triggered
        )
        
        return self.current_segment
    
    def write_frame(self, frame: np.ndarray):
        if self.writer:
            self.writer.write(frame)
    
    def write_frames(self, frames: list):
        for frame in frames:
            self.write_frame(frame)
    
    def finish_segment(self) -> Optional[CaptureSegment]:
        if not self.writer or not self.current_segment:
            return None
        
        self.writer.release()
        self.writer = None
        
        self.current_segment.end_time = datetime.now()
        if self.current_segment.end_time and self.current_segment.start_time:
            duration = (self.current_segment.end_time - self.current_segment.start_time).total_seconds()
            self.current_segment.duration = int(duration)
        
        # Get file size
        filepath = self.output_dir / self.current_segment.filename
        if filepath.exists():
            self.current_segment.file_size = filepath.stat().st_size
        
        completed_segment = self.current_segment
        self.current_segment = None
        return completed_segment