# database/repositories/__init__.py
from .base import BaseRepository
from .video_repository import VideoRepository
from .detection_repository import DetectionRepository

# Only import UserRepository if passlib is available (AI processor only)
try:
    from .user_repository import UserRepository
except ImportError:
    # UserRepository not available on Pi capture system
    UserRepository = None