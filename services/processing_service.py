# services/processing_service.py
import cv2
import time
import threading
import subprocess
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from core.models import VideoFile, BirdDetection, ProcessingStatus
from config.settings import ProcessingConfig
from services.ai_model_manager import AIModelManager
from database.repositories.video_repository import VideoRepository
from database.repositories.detection_repository import DetectionRepository

class ProcessingService:
    def __init__(
        self,
        config: ProcessingConfig,
        model_manager: AIModelManager,
        video_repo: VideoRepository,
        detection_repo: DetectionRepository
    ):
        self.config = config
        self.model_manager = model_manager
        self.video_repo = video_repo
        self.detection_repo = detection_repo
        
        # Processing state
        self.is_processing = False
        self.processing_lock = threading.Lock()
        
        # Directories
        self.incoming_dir = config.storage_path / "incoming"
        self.processed_dir = config.storage_path / "processed"
        self.thumbnails_dir = config.storage_path / "thumbnails"
        
        for directory in [self.incoming_dir, self.processed_dir, self.thumbnails_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def receive_video(self, file_data: bytes, filename: str) -> str:
        """Receive and store uploaded video file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{timestamp}_{filename}"
        file_path = self.incoming_dir / unique_filename
        
        # Save file
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        # Create database record
        video = VideoFile(
            id=None,
            filename=unique_filename,
            original_filename=filename,
            file_path=file_path,
            file_size=len(file_data),
            duration=None,
            fps=None,
            resolution=None,
            received_time=datetime.now(),
            status=ProcessingStatus.PENDING
        )
        
        video_id = self.video_repo.create(video)
        print(f"📥 Received: {filename} -> {unique_filename} ({len(file_data)/1024/1024:.1f}MB)")
        
        return unique_filename
    
    def convert_to_h264_for_web(self, filename):
        """Convert videos to H.264 for web browser compatibility"""
        file_path = self.processed_dir / filename
        if not file_path.exists():
            print(f"❌ File not found for conversion: {filename}")
            return False
        
        try:
            # Check current codec
            result = subprocess.run([
                'ffprobe', '-v', 'quiet', '-select_streams', 'v:0', 
                '-show_entries', 'stream=codec_name', '-of', 'csv=p=0', 
                str(file_path)
            ], capture_output=True, text=True, timeout=10)
            
            codec = result.stdout.strip()
            if codec == 'h264':
                print(f"✅ {filename} already uses H.264")
                return True
                
            print(f"🔄 Converting {filename} from {codec} to H.264 for web compatibility...")
            
            # Create temporary output file
            temp_path = file_path.with_suffix('.h264.mp4')
            
            # Convert to H.264 with web optimization
            subprocess.run([
                'ffmpeg', '-i', str(file_path), 
                '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
                '-c:a', 'aac', '-movflags', '+faststart',  # Web-optimized
                '-y',  # Overwrite output file
                str(temp_path)
            ], check=True, timeout=300, capture_output=True)
            
            # Replace original with converted version
            file_path.unlink()
            temp_path.rename(file_path)
            
            print(f"✅ Converted {filename} to H.264")
            return True
            
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            print(f"❌ Failed to convert {filename}: {e}")
            if 'temp_path' in locals() and temp_path.exists():
                temp_path.unlink()
            return False
        except Exception as e:
            print(f"❌ Unexpected error converting {filename}: {e}")
            return False
    
    def process_pending_videos(self):
        """Process all pending videos"""
        if self.is_processing:
            return
        
        with self.processing_lock:
            pending_videos = self.video_repo.get_pending_videos()
            if not pending_videos:
                return
        
        self.is_processing = True
        
        # Load model if needed
        if not self.model_manager.is_loaded:
            print("🤖 Loading AI model...")
            self.model_manager.load_model()
        
        print(f"🔄 Processing {len(pending_videos)} videos...")
        
        for video in pending_videos:
            try:
                self._process_single_video(video)
            except Exception as e:
                print(f"❌ Error processing {video.filename}: {e}")
                self.video_repo.update_status(video.id, ProcessingStatus.FAILED)
        
        self.is_processing = False
        print("✅ Batch processing complete")
    
    def _process_single_video(self, video: VideoFile):
        """Process a single video for bird detection"""
        video_path = self.incoming_dir / video.filename
        if not video_path.exists():
            return
        
        print(f"🔍 Processing: {video.filename}")
        start_time = time.time()
        
        # Update status to processing
        self.video_repo.update_status(video.id, ProcessingStatus.PROCESSING)
        
        # Open video
        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = total_frames / fps if fps > 0 else 0
        
        detections = []
        frame_number = 0
        
        # Process every nth frame
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_number % self.config.process_every_nth_frame == 0:
                timestamp = frame_number / fps if fps > 0 else frame_number * 0.1
                
                # Run detection
                frame_detections = self.model_manager.predict(frame)
                
                for detection_data in frame_detections:
                    detection = BirdDetection(
                        id=None,
                        video_id=video.id,
                        frame_number=frame_number,
                        timestamp=timestamp,
                        confidence=detection_data['confidence'],
                        bbox=tuple(detection_data['bbox']),
                        species='bird'
                    )
                    
                    # Store frame for thumbnail generation
                    detection_data['frame'] = frame.copy()
                    detections.append((detection, detection_data))
            
            frame_number += 1
            
            # Progress indicator
            if frame_number % 300 == 0:
                progress = (frame_number / total_frames) * 100
                print(f"  📊 Progress: {progress:.1f}%")
        
        cap.release()
        processing_time = time.time() - start_time
        
        # Save detections to database
        for detection, detection_data in detections:
            detection_id = self.detection_repo.create(detection)
            
            # Generate thumbnail for first few detections
            if len([d for d, _ in detections[:self.config.max_thumbnails_per_video]]) <= self.config.max_thumbnails_per_video:
                thumbnail_path = self._generate_thumbnail(
                    detection_data['frame'], detection.bbox, 
                    video.filename, detection_id, detection.confidence, detection.timestamp
                )
                if thumbnail_path:
                    self.detection_repo.update_thumbnail_path(detection_id, thumbnail_path)
        
        # Update video record
        self.video_repo.update_status(
            video.id, ProcessingStatus.COMPLETED, 
            processing_time, len(detections)
        )
        
        # Move processed video
        processed_path = self.processed_dir / video.filename
        video_path.rename(processed_path)
        
        # Convert to H.264 for web browser compatibility
        conversion_success = self.convert_to_h264_for_web(video.filename)
        if not conversion_success:
            print(f"⚠️ Warning: {video.filename} conversion failed - video may not stream properly in browsers")
        
        print(f"✅ {video.filename}: {len(detections)} birds found in {processing_time:.1f}s")
    
    def _generate_thumbnail(self, frame, bbox, video_filename, detection_id, confidence, timestamp):
        """Generate thumbnail for detection"""
        try:
            # Draw bounding box
            cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
            cv2.putText(frame, f"Bird {confidence:.2f}", 
                       (bbox[0], bbox[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(frame, f"t={timestamp:.1f}s", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Save thumbnail
            thumb_filename = f"{video_filename}_{detection_id}.jpg"
            thumb_path = self.thumbnails_dir / thumb_filename
            cv2.imwrite(str(thumb_path), frame)
            
            return thumb_filename
        except Exception as e:
            print(f"Failed to generate thumbnail: {e}")
            return None