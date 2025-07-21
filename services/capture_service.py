# services/capture_service.py
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
from utils.capture_logger import logger

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
        
        # Active-passive camera setup
        self.camera_id = capture_config.camera_id
        self.is_active = self.camera_id == 0  # Camera 0 is the active camera
        self.passive_camera_service: Optional['CaptureService'] = None
        
        # Pre-motion buffer (15 seconds worth of frames)
        buffer_size = capture_config.fps * 15  # 15 seconds of frames
        self.pre_motion_buffer = deque(maxlen=buffer_size)
        
        # Sync queue
        self.sync_queue: List[str] = []
        self.sync_lock = threading.Lock()
        
        # Callbacks
        self.on_motion_detected: Optional[Callable] = None
        self.on_segment_completed: Optional[Callable[[CaptureSegment], None]] = None
        
        logger.capture("CaptureService initialized")
        logger.camera(f"Camera ID: {self.camera_id} ({'ACTIVE' if self.is_active else 'PASSIVE'})")
        logger.config(f"Resolution: {capture_config.resolution}")
        logger.config(f"FPS: {capture_config.fps}")
        logger.config(f"Motion timeout: {motion_config.motion_timeout_seconds}s")
        logger.config(f"Buffer size: {buffer_size} frames")
        if self.is_active:
            logger.motion("Motion detection: ENABLED (active camera)")
        else:
            logger.motion("Motion detection: DISABLED (passive camera)")
    
    def start_capture(self):
        """Start the capture process in a background thread"""
        if self.is_running:
            logger.warning("Capture already running")
            return
        
        logger.capture("Starting capture thread...")
        self.is_running = True
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        logger.ok("Capture thread started")
    
    def stop_capture(self):
        """Stop the capture process"""
        logger.stop("Stopping capture...")
        self.is_running = False
        
        if hasattr(self, 'capture_thread'):
            self.capture_thread.join(timeout=5)
        
        # Finish any current segment
        if self.is_capturing:
            self._finish_current_segment()
        
        logger.ok("Capture stopped")
    
    def _capture_loop(self):
        """Main capture loop with active-passive camera support"""
        logger.capture(f"Capture loop started for camera {self.camera_id} ({'ACTIVE' if self.is_active else 'PASSIVE'})")
        last_heartbeat = time.time()
        
        while self.is_running:
            current_time = time.time()
            
            # Initialize has_motion to ensure it's always defined
            has_motion = False
            
            # Read frame from camera
            ret, frame = self.camera_manager.read_frame()
            if not ret:
                time.sleep(0.1)
                continue
            
            # Only active camera does motion detection
            if self.is_active:
                has_motion = self.motion_detector.detect_motion(frame)
                self.latest_motion = has_motion
                
                # Handle motion detection on active camera
                if has_motion:
                    self.last_motion_time = current_time
                    
                    if self.on_motion_detected:
                        self.on_motion_detected()
                    
                    # Start recording on both cameras
                    if not self.is_capturing:
                        logger.motion(f"Motion detected on active camera {self.camera_id}! Starting recording on both cameras...")
                        self._start_recording()
                        
                        # Trigger passive camera recording
                        if self.passive_camera_service and not self.passive_camera_service.is_capturing:
                            self.passive_camera_service._start_recording_from_active()
            else:
                # Passive camera doesn't do motion detection
                has_motion = False
                self.latest_motion = False
            
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
                
                # Simple timeout logic (back to old-state simplicity)
                if time_since_motion > self.motion_config.motion_timeout_seconds:
                    should_stop = True
                    stop_reason = f"no motion for {time_since_motion:.1f}s"
                elif recording_duration > self.motion_config.max_segment_duration:
                    should_stop = True
                    stop_reason = f"max duration reached ({recording_duration:.1f}s)"
                
                if should_stop:
                    logger.stop(f"Stopping recording on camera {self.camera_id}: {stop_reason}")
                    self._finish_current_segment()
                    
                    # If active camera stops, stop passive camera too
                    if self.is_active and self.passive_camera_service and self.passive_camera_service.is_capturing:
                        logger.stop(f"Stopping passive camera {self.passive_camera_service.camera_id} recording")
                        self.passive_camera_service._finish_current_segment()
            
            # Heartbeat every 30 seconds
            if current_time - last_heartbeat > 30:
                motion_age = current_time - self.last_motion_time if self.last_motion_time > 0 else 999
                frames_written = self.video_writer.get_frames_written() if self.is_capturing else 0
                
                logger.info(f"Status: Motion={has_motion}, Recording={self.is_capturing}, "
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
            
            # Clear pre-motion buffer to prevent timestamp issues
            if self.pre_motion_buffer:
                buffer_count = len(self.pre_motion_buffer)
                self.pre_motion_buffer.clear()
                logger.warning(f"Cleared {buffer_count} pre-motion frames")
            
            logger.video(f"Recording started: {segment.filename}")
            
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
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
                logger.warning("No segment to finish")
                return
            
            # Only keep segments longer than 5 seconds
            min_duration = 5
            if completed_segment.duration and completed_segment.duration > min_duration:
                # Add to sync queue
                with self.sync_lock:
                    self.sync_queue.append(completed_segment.filename)
                
                logger.ok(f"Segment saved: {completed_segment.filename}")
                
                if self.on_segment_completed:
                    self.on_segment_completed(completed_segment)
            else:
                # Delete short segments
                filepath = self.video_writer.output_dir / completed_segment.filename
                if filepath.exists():
                    filepath.unlink()
                duration = completed_segment.duration or 0
                frames = self.video_writer.get_frames_written()
                logger.cleanup(f"Deleted short segment: {completed_segment.filename} ({duration}s, {frames} frames)")
            
            # Recording finished, main loop will handle new motion
            logger.ok("Segment finished, waiting for new motion...")
                
        except Exception as e:
            logger.error(f"Error finishing segment: {e}")
            self.is_capturing = False

    def sync_files(self):
        """Sync pending files to processing server"""
        with self.sync_lock:
            files_to_sync = self.sync_queue.copy()
            self.sync_queue.clear()
        
        if not files_to_sync:
            logger.info("No files to sync")
            return
        
        logger.sync(f"Syncing {len(files_to_sync)} files...")
        for filename in files_to_sync:
            try:
                self._sync_single_file(filename)
            except Exception as e:
                logger.error(f"Failed to sync {filename}: {e}")
                # Put back in queue
                with self.sync_lock:
                    self.sync_queue.append(filename)
    
    def _sync_single_file(self, filename: str):
        """Sync a single file to processing server"""
        file_path = self.video_writer.output_dir / filename
        if not file_path.exists():
            logger.error(f"File not found for sync: {filename}")
            return
        
        logger.sync(f"Syncing {filename}...")
        success = self.sync_service.sync_file(file_path, filename)
        
        if success:
            # Move to synced directory
            synced_dir = self.video_writer.output_dir.parent / "synced"
            synced_dir.mkdir(exist_ok=True)
            new_path = synced_dir / filename
            file_path.rename(new_path)
            logger.ok(f"Synced and moved: {filename}")
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
    
    def set_passive_camera(self, passive_service: 'CaptureService'):
        """Set the passive camera service for active-passive recording"""
        if self.is_active:
            self.passive_camera_service = passive_service
            logger.link(f"Active camera {self.camera_id} linked to passive camera {passive_service.camera_id}")
        else:
            logger.warning(f"Camera {self.camera_id} is not active, cannot set passive camera")
    
    def _start_recording_from_active(self):
        """Start recording on passive camera when triggered by active"""
        if self.is_active:
            logger.warning(f"Active camera {self.camera_id} should not be triggered by active")
            return
        
        logger.trigger(f"Starting passive camera {self.camera_id} recording (triggered by active)")
        self._start_recording()
