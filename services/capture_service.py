# services/capture_service.py - FIXED VERSION

import time
import threading
from collections import deque
from typing import List, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path

from core.models import CaptureSegment, SystemStatus
from config.settings import CaptureConfig, MotionConfig
from services.motion_detector import MotionDetector
from services.camera_manager import CameraManager
from services.video_writer import VideoWriter
from services.file_sync import FileSyncService
from database.repositories.video_repository import VideoRepository

class CaptureService:
    def __init__(
        self,
        capture_config: CaptureConfig,
        motion_config: MotionConfig,
        camera_manager: CameraManager,
        motion_detector: MotionDetector,
        video_writer: VideoWriter,
        sync_service: FileSyncService,
        video_repo: VideoRepository
    ):
        self.capture_config = capture_config
        self.motion_config = motion_config
        self.camera_manager = camera_manager
        self.motion_detector = motion_detector
        self.video_writer = video_writer
        self.sync_service = sync_service
        self.video_repo = video_repo
        
        # State
        self.is_capturing = False
        self.is_running = False
        self.last_motion_time = 0
        self.frame_count = 0
        self.current_segment: Optional[CaptureSegment] = None
        
        # Pre-motion buffer
        buffer_frames = capture_config.fps * motion_config.motion_timeout_seconds // 2  # 15 seconds at 10fps
        self.pre_motion_buffer = deque(maxlen=buffer_frames)
        
        # Sync queue
        self.sync_queue: List[str] = []
        self.sync_lock = threading.Lock()
        
        # Callbacks
        self.on_motion_detected: Optional[Callable] = None
        self.on_segment_completed: Optional[Callable[[CaptureSegment], None]] = None
    
    def start_capture(self):
        """Start the capture process in a background thread"""
        if self.is_running:
            return
        
        self.is_running = True
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
    
    def stop_capture(self):
        """Stop the capture process"""
        self.is_running = False
        if hasattr(self, 'capture_thread'):
            self.capture_thread.join(timeout=5)
        
        # Finish any current segment
        if self.is_capturing:
            self._finish_current_segment()
    
    def _capture_loop(self):
        """Main capture loop - FIXED VERSION"""
        last_heartbeat = time.time()
        
        while self.is_running:
            current_time = time.time()
            
            # Read frame
            ret, frame = self.camera_manager.read_frame()
            if not ret:
                time.sleep(0.1)
                continue
            
            # Detect motion
            has_motion = self.motion_detector.detect_motion(frame)
            
            if has_motion:
                self.last_motion_time = current_time
                if self.on_motion_detected:
                    self.on_motion_detected()
                
                # Start recording if not already
                if not self.is_capturing:
                    self._start_recording()
            else:
                # Maintain pre-motion buffer only when NOT recording
                if not self.is_capturing:
                    self.pre_motion_buffer.append(frame.copy())
            
            # Write frame if recording (THIS IS THE KEY PART)
            if self.is_capturing:
                self.video_writer.write_frame(frame)
                self.frame_count += 1
                
                # Check if we should stop recording
                should_stop = False
                
                # Stop after 30 seconds of no motion
                if current_time - self.last_motion_time > self.motion_config.motion_timeout_seconds:
                    print(f"📹 Stopping recording - no motion for {current_time - self.last_motion_time:.1f}s")
                    should_stop = True
                
                # Or stop after max duration (5 minutes)
                elif self.frame_count > self.motion_config.max_segment_duration * self.capture_config.fps:
                    print(f"📹 Stopping recording - max duration reached ({self.frame_count} frames)")
                    should_stop = True
                
                if should_stop:
                    self._finish_current_segment()
                    
                    # Start new segment if motion is still recent (within 60 seconds)
                    if current_time - self.last_motion_time < 60:
                        print("📹 Starting new segment - motion still recent")
                        self._start_recording()
                    else:
                        print("📹 Stopping capture - no recent motion")
                        self.is_capturing = False
                        self.frame_count = 0
            
            # Heartbeat logging every 30 seconds
            if current_time - last_heartbeat > 30:
                motion_age = current_time - self.last_motion_time if self.last_motion_time > 0 else 999
                print(f"💓 Capture: Motion={has_motion}, Recording={self.is_capturing}, "
                      f"Last motion: {motion_age:.1f}s ago, Frames: {self.frame_count}")
                last_heartbeat = current_time
            
            # Small sleep to prevent overwhelming CPU
            time.sleep(1.0 / self.capture_config.fps)  # Maintain proper FPS timing
    
    def _start_recording(self):
        """Start recording a new segment"""
        self.current_segment = self.video_writer.start_segment(motion_triggered=True)
        self.is_capturing = True
        self.frame_count = 0
        
        # Write pre-motion buffer
        if self.pre_motion_buffer:
            print(f"📹 Writing {len(self.pre_motion_buffer)} pre-motion frames")
            self.video_writer.write_frames(list(self.pre_motion_buffer))
            self.frame_count += len(self.pre_motion_buffer)
            self.pre_motion_buffer.clear()
        
        print(f"📹 Started recording: {self.current_segment.filename}")
    
    def _finish_current_segment(self):
        """Finish the current recording segment"""
        if not self.current_segment:
            return
        
        completed_segment = self.video_writer.finish_segment()
        if not completed_segment:
            return
        
        # Only keep segments longer than 10 seconds
        if completed_segment.duration and completed_segment.duration > 10:
            # Add to sync queue
            with self.sync_lock:
                self.sync_queue.append(completed_segment.filename)
            
            print(f"✅ Completed: {completed_segment.filename} "
                  f"({completed_segment.duration}s, {self.frame_count} frames, "
                  f"{completed_segment.file_size/1024/1024:.1f}MB)")
            
            if self.on_segment_completed:
                self.on_segment_completed(completed_segment)
        else:
            # Delete short segments
            filepath = self.video_writer.output_dir / completed_segment.filename
            if filepath.exists():
                filepath.unlink()
            print(f"🗑️ Deleted short segment: {completed_segment.filename} "
                  f"({completed_segment.duration}s, {self.frame_count} frames)")
        
        self.current_segment = None
        self.frame_count = 0
    
    def sync_files(self):
        """Sync pending files to processing server"""
        with self.sync_lock:
            files_to_sync = self.sync_queue.copy()
            self.sync_queue.clear()
        
        for filename in files_to_sync:
            try:
                self._sync_single_file(filename)
            except Exception as e:
                print(f"❌ Failed to sync {filename}: {e}")
                # Put back in queue
                with self.sync_lock:
                    self.sync_queue.append(filename)
    
    def _sync_single_file(self, filename: str):
        """Sync a single file to processing server"""
        file_path = self.video_writer.output_dir / filename
        if not file_path.exists():
            return
        
        print(f"📤 Syncing {filename}...")
        success = self.sync_service.sync_file(file_path, filename)
        
        if success:
            # Move to synced directory
            synced_dir = self.video_writer.output_dir.parent / "synced"
            synced_dir.mkdir(exist_ok=True)
            file_path.rename(synced_dir / filename)
            print(f"✅ Synced: {filename}")
        else:
            raise Exception("Upload failed")
    
    def get_status(self) -> SystemStatus:
        """Get current system status"""
        with self.sync_lock:
            queue_size = len(self.sync_queue)
        
        return SystemStatus(
            is_capturing=self.is_capturing,
            last_motion_time=datetime.fromtimestamp(self.last_motion_time) if self.last_motion_time else None,
            queue_size=queue_size
        )
    
    def get_pending_sync_count(self) -> int:
        """Get number of files pending sync"""
        with self.sync_lock:
            return len(self.sync_queue)