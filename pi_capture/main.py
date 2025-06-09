# pi_capture/main.py
#!/usr/bin/env python3
"""
Raspberry Pi Capture System Entry Point
"""
import schedule
import threading
import time
from pathlib import Path

from config.settings import load_capture_config
from database.connection import DatabaseManager
from database.repositories.video_repository import VideoRepository
from services.motion_detector import MotionDetector
from services.camera_manager import CameraManager
from services.video_writer import VideoWriter
from services.file_sync import FileSyncService
from services.capture_service import CaptureService
from web.app import create_capture_app

def setup_services(config):
    """Initialize all services"""
    # Database
    db_manager = DatabaseManager(config.database.path)
    video_repo = VideoRepository(db_manager)
    video_repo.create_table()
    
    # Core services
    motion_detector = MotionDetector(config.motion)
    camera_manager = CameraManager(config.capture)
    
    # Video writing
    raw_dir = config.processing.storage_path / "raw_footage"
    video_writer = VideoWriter(
        raw_dir, 
        config.capture.fps, 
        config.capture.resolution
    )
    
    # Sync service
    sync_service = FileSyncService(
        config.sync.processing_server_host,
        config.sync.processing_server_port,
        config.sync.upload_timeout_seconds
    )
    
    # Main capture service
    capture_service = CaptureService(
        config.capture,
        config.motion,
        camera_manager,
        motion_detector,
        video_writer,
        sync_service,
        video_repo
    )
    
    return capture_service, sync_service

def setup_scheduler(capture_service, config):
    """Setup scheduled tasks"""
    # Schedule sync every N minutes
    schedule.every(config.sync.sync_interval_minutes).minutes.do(
        capture_service.sync_files
    )
    
    # Schedule cleanup daily
    schedule.every().day.at("03:00").do(
        lambda: cleanup_old_files(config.processing.storage_path, config.sync.cleanup_days)
    )
    
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(60)
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

def cleanup_old_files(storage_path: Path, days_to_keep: int):
    """Clean up old files"""
    from datetime import datetime, timedelta
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    
    synced_dir = storage_path / "synced"
    if synced_dir.exists():
        for file_path in synced_dir.glob("*.mp4"):
            if datetime.fromtimestamp(file_path.stat().st_mtime) < cutoff_date:
                file_path.unlink()
                print(f"🗑️ Cleaned up: {file_path.name}")

def main():
    print("🚀 Starting Pi Capture System...")
    
    # Load configuration
    config = load_capture_config()
    
    # Setup services
    capture_service, sync_service = setup_services(config)
    
    # Setup scheduler
    setup_scheduler(capture_service, config)
    
    # Start capture
    capture_service.start_capture()
    
    # Start web interface
    app = create_capture_app(capture_service, sync_service, config)
    
    print(f"✅ System ready! Web interface: http://0.0.0.0:{config.web.capture_port}")
    
    try:
        app.run(
            host=config.web.host,
            port=config.web.capture_port,
            threaded=True,
            debug=False
        )
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        capture_service.stop_capture()

if __name__ == '__main__':
    main()

# ai_processor/main.py
#!/usr/bin/env python3
"""
AI Processing Server Entry Point
"""
import schedule
import threading
import time

from config.settings import load_processing_config
from database.connection import DatabaseManager
from database.repositories.video_repository import VideoRepository
from database.repositories.detection_repository import DetectionRepository
from services.ai_model_manager import AIModelManager
from services.processing_service import ProcessingService
from web.app import create_processing_app

def setup_services(config):
    """Initialize all services"""
    # Database
    db_manager = DatabaseManager(config.database.path)
    video_repo = VideoRepository(db_manager)
    detection_repo = DetectionRepository(db_manager)
    
    # Create tables
    video_repo.create_table()
    detection_repo.create_table()
    
    # AI services
    model_manager = AIModelManager(
        config.processing.model_name,
        config.processing.confidence_threshold
    )
    
    # Processing service
    processing_service = ProcessingService(
        config.processing,
        model_manager,
        video_repo,
        detection_repo
    )
    
    return processing_service, video_repo, detection_repo

def setup_scheduler(processing_service, config):
    """Setup scheduled tasks"""
    # Auto-process every 30 minutes
    schedule.every(30).minutes.do(processing_service.process_pending_videos)
    
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(60)
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

def main():
    print("🧠 Starting AI Processing Server...")
    
    # Load configuration
    config = load_processing_config()
    
    # Setup services
    processing_service, video_repo, detection_repo = setup_services(config)
    
    # Setup scheduler
    setup_scheduler(processing_service, config)
    
    # Start web interface
    app = create_processing_app(processing_service, video_repo, detection_repo, config)
    
    print(f"✅ Processing server ready! Web interface: http://0.0.0.0:{config.web.processing_port}")
    
    try:
        app.run(
            host=config.web.host,
            port=config.web.processing_port,
            threaded=True,
            debug=False
        )
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")

if __name__ == '__main__':
    main()


