# services/video_writer.py - FIXED VERSION
import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Tuple
from core.models import CaptureSegment
from datetime import datetime

class VideoWriter:
    def __init__(self, output_dir: Path, fps: int = 10, resolution: Tuple[int, int] = (640, 480)):
        self.output_dir = output_dir
        self.fps = fps
        self.resolution = resolution
        self.writer: Optional[cv2.VideoWriter] = None
        self.current_segment: Optional[CaptureSegment] = None
        self.frames_written = 0
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Video writer initialized - Output: {self.output_dir}, FPS: {self.fps}")
    
    def start_segment(self, motion_triggered: bool = False) -> CaptureSegment:
        if self.writer:
            print("⚠️ Finishing previous segment before starting new one")
            self.finish_segment()
        
        timestamp = datetime.now()
        filename = f"segment_{timestamp.strftime('%Y%m%d_%H%M%S')}.mp4"
        filepath = self.output_dir / filename
        
        # Use mp4v codec (server will convert to H.264 later)
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
        print(f"🎬 Started video segment: {filename}")
        
        return self.current_segment
    
    def write_frame(self, frame: np.ndarray):
        """Write a single frame to the video"""
        if not self.writer or not self.writer.isOpened():
            print("❌ No video writer available for frame")
            return
        
        # Ensure frame is the right size
        if frame.shape[:2] != (self.resolution[1], self.resolution[0]):
            frame = cv2.resize(frame, self.resolution)
        
        try:
            self.writer.write(frame)
            self.frames_written += 1
            
            # Debug every 50 frames
            if self.frames_written % 50 == 0:
                print(f"📝 Written {self.frames_written} frames to {self.current_segment.filename if self.current_segment else 'unknown'}")
                
        except Exception as e:
            print(f"❌ Error writing frame: {e}")
    
    def write_frames(self, frames: list):
        """Write multiple frames to the video"""
        if not frames:
            return
        
        print(f"📝 Writing {len(frames)} frames...")
        for i, frame in enumerate(frames):
            self.write_frame(frame)
            
            # Progress for large batches
            if len(frames) > 10 and i % 10 == 0:
                print(f"  📝 Progress: {i+1}/{len(frames)} frames")
    
    def finish_segment(self) -> Optional[CaptureSegment]:
        if not self.writer or not self.current_segment:
            return None
        
        print(f"🏁 Finishing segment: {self.current_segment.filename} ({self.frames_written} frames)")
        
        # Release the writer
        self.writer.release()
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
            print(f"✅ Segment completed: {self.current_segment.filename}")
            print(f"   📊 Duration: {self.current_segment.duration}s, Frames: {self.frames_written}, Size: {self.current_segment.file_size/1024/1024:.1f}MB")
        else:
            print(f"❌ Video file not found: {filepath}")
        
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