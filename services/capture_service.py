# services/capture_service.py - FIXED VERSION 2
import time
import threading
from collections import deque
from typing import List, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np

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
        
        # State tracking
        self.is_capturing = False
        self.is_running = False
        self.last_motion_time = 0
        self.segment_start_time = 0
        # Latest motion state for UI indicators
        self.latest_motion = False
        
        # Pre-motion buffer (15 seconds worth of frames)
        buffer_size = capture_config.fps * 15  # 15 seconds of frames
        self.pre_motion_buffer = deque(maxlen=buffer_size)
        
        # Sync queue
        self.sync_queue: List[str] = []
        self.sync_lock = threading.Lock()
        
        # Callbacks
        self.on_motion_detected: Optional[Callable] = None
        self.on_segment_completed: Optional[Callable[[CaptureSegment], None]] = None
        
        print(f"🎯 CaptureService initialized:")
        print(f"   📺 Resolution: {capture_config.resolution}")
        print(f"   🎬 FPS: {capture_config.fps}")
        print(f"   ⏱️ Motion timeout: {motion_config.motion_timeout_seconds}s")
        print(f"   📦 Buffer size: {buffer_size} frames")
    
    def start_capture(self):
        """Start the capture process in a background thread"""
        if self.is_running:
            print("⚠️ Capture already running")
            return
        
        print("🚀 Starting capture thread...")
        self.is_running = True
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        print("✅ Capture thread started")
    
    def stop_capture(self):
        """Stop the capture process"""
        print("🛑 Stopping capture...")
        self.is_running = False
        
        if hasattr(self, 'capture_thread'):
            self.capture_thread.join(timeout=5)
        
        # Finish any current segment
        if self.is_capturing:
            self._finish_current_segment()
        
        print("✅ Capture stopped")
    
    def _capture_loop(self):
        """Main capture loop - FINAL VERSION"""
        print("🔄 Capture loop started")
        last_heartbeat = time.time()
        
        while self.is_running:
            current_time = time.time()
            
            # Read frame from camera
            ret, frame = self.camera_manager.read_frame()
            if not ret:
                time.sleep(0.1)
                continue
            
            # Detect motion
            has_motion = self.motion_detector.detect_motion(frame)
            self.latest_motion = has_motion
            
            # Handle motion detection
            if has_motion:
                self.last_motion_time = current_time
                
                if self.on_motion_detected:
                    self.on_motion_detected()
                
                # Start recording if not already recording
                if not self.is_capturing:
                    print(f"🎯 Motion detected! Starting recording...")
                    self._start_recording()
            
            # Always add frames to pre-motion buffer when NOT recording
            if not self.is_capturing:
                self.pre_motion_buffer.append(frame.copy())
            
            # If we're recording, write the frame
            if self.is_capturing:
                self.video_writer.write_frame(frame)
                
                # Calculate how long we've been recording
                recording_duration = current_time - self.segment_start_time
                time_since_motion = current_time - self.last_motion_time
                
                # Stop recording if:
                # 1. No motion for 30 seconds, OR
                # 2. Recording for more than 5 minutes
                should_stop = False
                stop_reason = ""
                
                if time_since_motion > self.motion_config.motion_timeout_seconds:
                    should_stop = True
                    stop_reason = f"no motion for {time_since_motion:.1f}s"
                elif recording_duration > self.motion_config.max_segment_duration:
                    should_stop = True
                    stop_reason = f"max duration reached ({recording_duration:.1f}s)"
                
                if should_stop:
                    print(f"🛑 Stopping recording: {stop_reason}")
                    self._finish_current_segment()
                    # DO NOT RESTART HERE - let the loop detect new motion naturally!
            
            # Heartbeat every 30 seconds
            if current_time - last_heartbeat > 30:
                motion_age = current_time - self.last_motion_time if self.last_motion_time > 0 else 999
                frames_written = self.video_writer.get_frames_written() if self.is_capturing else 0
                
                print(f"💓 Status: Motion={has_motion}, Recording={self.is_capturing}, "
                    f"LastMotion={motion_age:.1f}s ago, Frames={frames_written}, "
                    f"Buffer={len(self.pre_motion_buffer)}")
                last_heartbeat = current_time
            
            # Control frame rate
            time.sleep(1.0 / self.capture_config.fps)
    
    def _start_recording(self):
        """Start recording a new segment"""
        try:
            # Create new segment
            segment = self.video_writer.start_segment(motion_triggered=True)
            self.is_capturing = True
            self.segment_start_time = time.time()
            
            # Write pre-motion buffer if we have frames
            if self.pre_motion_buffer:
                print(f"📼 Writing {len(self.pre_motion_buffer)} pre-motion frames")
                self.video_writer.write_frames(list(self.pre_motion_buffer))
                self.pre_motion_buffer.clear()
            
            print(f"🎬 Recording started: {segment.filename}")
            
        except Exception as e:
            print(f"❌ Failed to start recording: {e}")
            self.is_capturing = False
    
    def _finish_current_segment(self):
        """Finish the current recording segment"""
        if not self.is_capturing:
            return
        
        try:
            completed_segment = self.video_writer.finish_segment()
            self.is_capturing = False
            self.segment_start_time = 0
            
            if not completed_segment:
                print("⚠️ No segment to finish")
                return
            
            # Only keep segments longer than 5 seconds
            min_duration = 5
            if completed_segment.duration and completed_segment.duration > min_duration:
                # Add to sync queue
                with self.sync_lock:
                    self.sync_queue.append(completed_segment.filename)
                
                print(f"✅ Segment saved: {completed_segment.filename}")
                
                if self.on_segment_completed:
                    self.on_segment_completed(completed_segment)
            else:
                # Delete short segments
                filepath = self.video_writer.output_dir / completed_segment.filename
                if filepath.exists():
                    filepath.unlink()
                duration = completed_segment.duration or 0
                frames = self.video_writer.get_frames_written()
                print(f"🗑️ Deleted short segment: {completed_segment.filename} ({duration}s, {frames} frames)")
            
            # DO NOT RESTART RECORDING HERE!
            # Let the main loop handle new motion detection
            print("✅ Segment finished, waiting for new motion...")
                
        except Exception as e:
            print(f"❌ Error finishing segment: {e}")
            self.is_capturing = False

    def sync_files(self):
        """Sync pending files to processing server"""
        with self.sync_lock:
            files_to_sync = self.sync_queue.copy()
            self.sync_queue.clear()
        
        if not files_to_sync:
            print("📭 No files to sync")
            return
        
        print(f"📤 Syncing {len(files_to_sync)} files...")
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
            print(f"❌ File not found for sync: {filename}")
            return
        
        print(f"📤 Syncing {filename}...")
        success = self.sync_service.sync_file(file_path, filename)
        
        if success:
            # Move to synced directory
            synced_dir = self.video_writer.output_dir.parent / "synced"
            synced_dir.mkdir(exist_ok=True)
            new_path = synced_dir / filename
            file_path.rename(new_path)
            print(f"✅ Synced and moved: {filename}")
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