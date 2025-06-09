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

