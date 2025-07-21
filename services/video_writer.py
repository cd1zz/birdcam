# services/video_writer.py
import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Tuple
from core.models import CaptureSegment
from datetime import datetime
from utils.capture_logger import logger

class VideoWriter:
    def __init__(self, output_dir: Path, fps: int = 5, resolution: Tuple[int, int] = (640, 480), camera_id: int = 0):
        self.output_dir = output_dir
        self.fps = fps
        self.resolution = resolution
        self.camera_id = camera_id
        self.writer: Optional[cv2.VideoWriter] = None
        self.current_segment: Optional[CaptureSegment] = None
        self.frames_written = 0
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.video("Video writer initialized", camera_id=self.camera_id, output_dir=str(self.output_dir), fps=self.fps)
    
    def start_segment(self, motion_triggered: bool = False) -> CaptureSegment:
        if self.writer:
            logger.warning("Finishing previous segment before starting new one")
            self.finish_segment()
        
        timestamp = datetime.now()
        filename = f"segment_{timestamp.strftime('%Y%m%d_%H%M%S')}_cam{self.camera_id}.mp4"
        filepath = self.output_dir / filename
        
        # Use mp4v codec (simple and reliable)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.writer = cv2.VideoWriter(str(filepath), fourcc, self.fps, self.resolution)
        
        if not self.writer.isOpened():
            raise RuntimeError(f"Failed to initialize video writer for {filename}")
        
        self.current_segment = CaptureSegment(
            filename=filename,
            start_time=timestamp,
            has_motion=motion_triggered
        )
        
        self.frames_written = 0
        logger.video(f"Started video segment: {filename}")
        
        return self.current_segment
    
    def write_frame(self, frame: np.ndarray):
        """Write a single frame to the video"""
        if not self.writer or not self.writer.isOpened():
            return
        
        # Basic validation
        if frame is None or frame.size == 0:
            return
            
        # Ensure frame is the right size
        if frame.shape[:2] != (self.resolution[1], self.resolution[0]):
            frame = cv2.resize(frame, self.resolution)
        
        # Write frame to video
        try:
            self.writer.write(frame)
            self.frames_written += 1
        except Exception as e:
            logger.error(f"Write error: {e}")
    
    def write_frames(self, frames: list):
        """Write multiple frames to the video"""
        if not frames:
            return
        
        for frame in frames:
            self.write_frame(frame)
    
    def write_frames_with_timestamps(self, frames: list):
        """Write frames with timestamp handling (currently disabled)"""
        if not frames:
            return
        
        # Timestamp-based frame writing is disabled to prevent codec issues
        logger.warning("Timestamp-based frame writing is disabled")
        logger.warning(f"Skipping {len(frames)} frames")
        return
    
    def finish_segment(self) -> Optional[CaptureSegment]:
        if not self.writer or not self.current_segment:
            return None
        
        logger.video(f"Finishing segment: {self.current_segment.filename}", frames=self.frames_written)
        
        # Safely release the writer
        try:
            if self.writer.isOpened():
                self.writer.release()
            self.writer = None
        except Exception as e:
            logger.warning(f"Error releasing video writer: {e}")
            self.writer = None
        
        # Update segment info
        self.current_segment.end_time = datetime.now()
        if self.current_segment.end_time and self.current_segment.start_time:
            duration = (self.current_segment.end_time - self.current_segment.start_time).total_seconds()
            self.current_segment.duration = int(duration)
        
        # Get file size
        filepath = self.output_dir / self.current_segment.filename
        if filepath.exists():
            self.current_segment.file_size = filepath.stat().st_size
            logger.ok(f"Segment completed: {self.current_segment.filename}")
        
        completed_segment = self.current_segment
        self.current_segment = None
        self.frames_written = 0
        
        return completed_segment
    
    def is_recording(self) -> bool:
        """Check if currently recording"""
        return self.writer is not None and self.writer.isOpened()
    
    def get_frames_written(self) -> int:
        """Get number of frames written to current segment"""
        return self.frames_written
    
    def get_videos_count_today(self) -> int:
        """Count the number of videos created today"""
        try:
            today = datetime.now().date()
            count = 0
            for video_file in self.output_dir.glob("segment_*.mp4"):
                # Extract date from filename: segment_YYYYMMDD_HHMMSS.mp4
                try:
                    date_str = video_file.stem.split('_')[1]  # Get YYYYMMDD part
                    file_date = datetime.strptime(date_str, '%Y%m%d').date()
                    if file_date == today:
                        count += 1
                except (IndexError, ValueError):
                    continue
            return count
        except Exception as e:
            print(f"Error counting today's videos: {e}")
            return 0