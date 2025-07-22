# core/models.py
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple
from enum import Enum

class ProcessingStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class VideoFile:
    id: Optional[int]
    filename: str
    original_filename: str
    file_path: Path
    file_size: int
    duration: Optional[float]
    fps: Optional[float]
    resolution: Optional[str]
    received_time: datetime
    status: ProcessingStatus = ProcessingStatus.PENDING
    processing_time: Optional[float] = None
    bird_count: int = 0
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class BirdDetection:
    id: Optional[int]
    video_id: int
    frame_number: int
    timestamp: float
    confidence: float
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    species: str = "bird"
    thumbnail_path: Optional[str] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class MotionRegion:
    x1: int
    y1: int
    x2: int
    y2: int
    
    @property
    def width(self) -> int:
        return self.x2 - self.x1
    
    @property
    def height(self) -> int:
        return self.y2 - self.y1
    
    @property
    def area(self) -> int:
        return self.width * self.height

@dataclass
class ProcessingStats:
    date: datetime
    videos_processed: int = 0
    total_birds: int = 0
    processing_time_total: float = 0.0
    avg_processing_time: float = 0.0
    
    def add_video(self, bird_count: int, processing_time: float):
        self.videos_processed += 1
        self.total_birds += bird_count
        self.processing_time_total += processing_time
        self.avg_processing_time = self.processing_time_total / self.videos_processed

@dataclass
class SystemStatus:
    is_capturing: bool = False
    is_processing: bool = False
    model_loaded: bool = False
    gpu_available: bool = False
    last_motion_time: Optional[datetime] = None
    queue_size: int = 0

@dataclass
class CaptureSegment:
    filename: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[int] = None
    has_motion: bool = False
    synced: bool = False
    file_size: Optional[int] = None

class UserRole(Enum):
    ADMIN = "admin"
    VIEWER = "viewer"

@dataclass
class User:
    id: Optional[int]
    username: str
    password_hash: str
    role: UserRole
    email: Optional[str] = None
    email_verified: bool = False
    verification_token: Optional[str] = None
    verification_token_expires: Optional[datetime] = None
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    is_active: bool = True
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def has_admin_access(self) -> bool:
        return self.role == UserRole.ADMIN
    
    def can_view(self) -> bool:
        return self.is_active
    
    def can_manage_users(self) -> bool:
        return self.role == UserRole.ADMIN
    
    def can_manage_settings(self) -> bool:
        return self.role == UserRole.ADMIN