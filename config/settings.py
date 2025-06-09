# config/settings.py
from dataclasses import dataclass
from pathlib import Path
import os
from typing import Tuple, Optional

@dataclass
class DatabaseConfig:
    path: Path
    
    def __post_init__(self):
        # Resolve to an absolute path so Flask can serve files correctly
        self.path = Path(self.path).resolve()

@dataclass
class CaptureConfig:
    stream_url: str
    segment_duration: int = 300
    fps: int = 10
    resolution: Tuple[int, int] = (640, 480)
    buffer_size: int = 2
    pre_motion_buffer_seconds: int = 15

@dataclass 
class MotionConfig:
    threshold: int = 5000
    min_contour_area: int = 500
    learning_rate: float = 0.01
    motion_timeout_seconds: int = 30
    max_segment_duration: int = 300
    region: Optional[Tuple[int, int, int, int]] = None

@dataclass
class ProcessingConfig:
    storage_path: Path
    model_name: str = 'yolov5n'
    confidence_threshold: float = 0.35
    process_every_nth_frame: int = 3
    max_thumbnails_per_video: int = 5
    
    def __post_init__(self):
        # Resolve storage path to an absolute location to avoid issues with
        # Flask's send_from_directory which interprets relative paths relative
        # to the application's root directory.
        self.storage_path = Path(self.storage_path).resolve()

@dataclass
class SyncConfig:
    processing_server_host: str
    processing_server_port: int = 8091
    sync_interval_minutes: int = 15
    cleanup_days: int = 3
    upload_timeout_seconds: int = 300

@dataclass
class WebConfig:
    host: str = "0.0.0.0"
    capture_port: int = 8090
    processing_port: int = 8091
    max_content_length: int = 500 * 1024 * 1024
    cors_enabled: bool = True

@dataclass
class AppConfig:
    database: DatabaseConfig
    capture: CaptureConfig
    motion: MotionConfig
    processing: ProcessingConfig
    sync: SyncConfig
    web: WebConfig

def load_capture_config() -> AppConfig:
    """Load configuration for Pi capture system"""
    base_path = Path(os.getenv('STORAGE_PATH', './bird_footage'))
    
    return AppConfig(
        database=DatabaseConfig(path=base_path / "capture.db"),
        capture=CaptureConfig(
            stream_url=os.getenv('STREAM_URL', 'rtsp://192.168.1.136:8554/birdcam')
        ),
        motion=MotionConfig(),
        processing=ProcessingConfig(storage_path=base_path),
        sync=SyncConfig(
            processing_server_host=os.getenv('PROCESSING_SERVER', '192.168.1.136')
        ),
        web=WebConfig()
    )

def load_processing_config() -> AppConfig:
    """Load configuration for processing server"""
    base_path = Path(os.getenv('STORAGE_PATH', './bird_processing'))
    
    return AppConfig(
        database=DatabaseConfig(path=base_path / "processing.db"),
        capture=CaptureConfig(stream_url=""),  # Not used on processing server
        motion=MotionConfig(),  # Not used on processing server
        processing=ProcessingConfig(storage_path=base_path),
        sync=SyncConfig(processing_server_host="localhost"),  # Not used on processing server
        web=WebConfig()
    )