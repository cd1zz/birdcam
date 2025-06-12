# config/settings.py
from dataclasses import dataclass
from pathlib import Path
import os
from typing import Tuple, Optional, List, Dict
from dotenv import load_dotenv

# Load .env file
load_dotenv()

def get_bool_env(key: str, default: bool = False) -> bool:
    """Get boolean from environment variable"""
    value = os.getenv(key, str(default)).lower()
    return value in ('true', '1', 'yes', 'on')

def get_int_env(key: str, default: int) -> int:
    """Get integer from environment variable"""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default

def get_float_env(key: str, default: float) -> float:
    """Get float from environment variable"""
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        return default

def get_list_env(key: str, default: List[str] = None) -> List[str]:
    """Get comma-separated list from environment variable"""
    if default is None:
        default = []
    value = os.getenv(key, '')
    if not value:
        return default
    return [item.strip() for item in value.split(',') if item.strip()]

def get_detection_confidences() -> Dict[str, float]:
    """Get confidence thresholds for each detection class"""
    detection_classes = get_list_env('DETECTION_CLASSES', ['bird'])
    default_confidence = get_float_env('DEFAULT_CONFIDENCE', 0.35)
    
    confidences = {}
    for detection_class in detection_classes:
        env_key = f"{detection_class.upper()}_CONFIDENCE"
        confidences[detection_class] = get_float_env(env_key, default_confidence)
    
    return confidences

@dataclass
class DatabaseConfig:
    path: Path
    
    def __post_init__(self):
        # Resolve to an absolute path so Flask can serve files correctly
        self.path = Path(self.path).resolve()

@dataclass
class CaptureConfig:
    camera_type: str
    stream_url: str
    segment_duration: int
    fps: int
    resolution: Tuple[int, int]
    buffer_size: int
    pre_motion_buffer_seconds: int

@dataclass 
class MotionConfig:
    threshold: int
    min_contour_area: int
    learning_rate: float
    motion_timeout_seconds: int
    max_segment_duration: int
    region: Optional[Tuple[int, int, int, int]] = None

@dataclass
class DetectionConfig:
    classes: List[str]
    confidences: Dict[str, float]
    model_name: str
    process_every_nth_frame: int
    max_thumbnails_per_video: int
    
    def get_confidence(self, detection_class: str) -> float:
        """Get confidence threshold for a specific detection class"""
        return self.confidences.get(detection_class, self.confidences.get('default', 0.35))

@dataclass
class ProcessingConfig:
    storage_path: Path
    detection: DetectionConfig
    detection_retention_days: int
    no_detection_retention_days: int
    
    def __post_init__(self):
        # Resolve storage path to an absolute location
        self.storage_path = Path(self.storage_path).resolve()

@dataclass
class SyncConfig:
    processing_server_host: str
    processing_server_port: int
    sync_interval_minutes: int
    cleanup_days: int
    upload_timeout_seconds: int

@dataclass
class WebConfig:
    host: str
    capture_port: int
    processing_port: int
    max_content_length: int
    cors_enabled: bool

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
            camera_type=os.getenv('CAMERA_TYPE', 'opencv'),
            stream_url='',  # RTSP environment variable removed
            segment_duration=get_int_env('SEGMENT_DURATION', 300),
            fps=get_int_env('FPS', 10),
            resolution=(get_int_env('RESOLUTION_WIDTH', 640), get_int_env('RESOLUTION_HEIGHT', 480)),
            buffer_size=get_int_env('BUFFER_SIZE', 2),
            pre_motion_buffer_seconds=get_int_env('PRE_MOTION_BUFFER_SECONDS', 15)
        ),
        motion=MotionConfig(
            threshold=get_int_env('MOTION_THRESHOLD', 5000),
            min_contour_area=get_int_env('MIN_CONTOUR_AREA', 500),
            learning_rate=get_float_env('LEARNING_RATE', 0.01),
            motion_timeout_seconds=get_int_env('MOTION_TIMEOUT_SECONDS', 30),
            max_segment_duration=get_int_env('MAX_SEGMENT_DURATION', 300)
        ),
        processing=ProcessingConfig(
            storage_path=base_path,
            detection=DetectionConfig(
                classes=get_list_env('DETECTION_CLASSES', ['bird']),
                confidences=get_detection_confidences(),
                model_name=os.getenv('MODEL_NAME', 'yolov5n'),
                process_every_nth_frame=get_int_env('PROCESS_EVERY_NTH_FRAME', 3),
                max_thumbnails_per_video=get_int_env('MAX_THUMBNAILS_PER_VIDEO', 5)
            ),
            detection_retention_days=get_int_env('DETECTION_RETENTION_DAYS', 30),
            no_detection_retention_days=get_int_env('NO_DETECTION_RETENTION_DAYS', 7)
        ),
        sync=SyncConfig(
            processing_server_host=os.getenv('PROCESSING_SERVER', '192.168.1.136'),
            processing_server_port=get_int_env('PROCESSING_PORT', 8091),
            sync_interval_minutes=get_int_env('SYNC_INTERVAL_MINUTES', 15),
            cleanup_days=get_int_env('PI_CLEANUP_DAYS', 3),
            upload_timeout_seconds=get_int_env('UPLOAD_TIMEOUT_SECONDS', 300)
        ),
        web=WebConfig(
            host=os.getenv('HOST', '0.0.0.0'),
            capture_port=get_int_env('CAPTURE_PORT', 8090),
            processing_port=get_int_env('PROCESSING_PORT', 8091),
            max_content_length=get_int_env('MAX_CONTENT_LENGTH', 500 * 1024 * 1024),
            cors_enabled=get_bool_env('CORS_ENABLED', True)
        )
    )

def load_processing_config() -> AppConfig:
    """Load configuration for processing server"""
    base_path = Path(os.getenv('STORAGE_PATH', './bird_processing'))
    
    return AppConfig(
        database=DatabaseConfig(path=base_path / "processing.db"),
        capture=CaptureConfig(
            camera_type=os.getenv('CAMERA_TYPE', 'opencv'),
            stream_url="",  # Not used on processing server
            segment_duration=300,
            fps=10,
            resolution=(640, 480),
            buffer_size=2,
            pre_motion_buffer_seconds=15
        ),
        motion=MotionConfig(
            threshold=5000,
            min_contour_area=500,
            learning_rate=0.01,
            motion_timeout_seconds=30,
            max_segment_duration=300
        ),
        processing=ProcessingConfig(
            storage_path=base_path,
            detection=DetectionConfig(
                classes=get_list_env('DETECTION_CLASSES', ['bird']),
                confidences=get_detection_confidences(),
                model_name=os.getenv('MODEL_NAME', 'yolov5n'),
                process_every_nth_frame=get_int_env('PROCESS_EVERY_NTH_FRAME', 3),
                max_thumbnails_per_video=get_int_env('MAX_THUMBNAILS_PER_VIDEO', 5)
            ),
            detection_retention_days=get_int_env('DETECTION_RETENTION_DAYS', 30),
            no_detection_retention_days=get_int_env('NO_DETECTION_RETENTION_DAYS', 7)
        ),
        sync=SyncConfig(
            processing_server_host=os.getenv('PROCESSING_SERVER', 'localhost'),
            processing_server_port=get_int_env('PROCESSING_PORT', 8091),
            sync_interval_minutes=get_int_env('SYNC_INTERVAL_MINUTES', 15),
            cleanup_days=get_int_env('PI_CLEANUP_DAYS', 3),
            upload_timeout_seconds=get_int_env('UPLOAD_TIMEOUT_SECONDS', 300)
        ),
        web=WebConfig(
            host=os.getenv('HOST', '0.0.0.0'),
            capture_port=get_int_env('CAPTURE_PORT', 8090),
            processing_port=get_int_env('PROCESSING_PORT', 8091),
            max_content_length=get_int_env('MAX_CONTENT_LENGTH', 500 * 1024 * 1024),
            cors_enabled=get_bool_env('CORS_ENABLED', True)
        )
    )