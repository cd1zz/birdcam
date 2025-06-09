# pi_capture/main.py - FIXED VERSION
#!/usr/bin/env python3
"""
Raspberry Pi Capture System Entry Point - FIXED
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
    """Initialize all services with proper debugging"""
    print("🔧 Setting up services...")
    
    # Database
    print("📊 Initializing database...")
    db_manager = DatabaseManager(config.database.path)
    video_repo = VideoRepository(db_manager)
    video_repo.create_table()
    print("✅ Database ready")
    
    # Core services
    print("🎯 Setting up motion detector...")
    motion_detector = MotionDetector(config.motion)
    print("✅ Motion detector ready")
    
    print("📹 Setting up camera manager...")
    camera_manager = CameraManager(config.capture)
    print("✅ Camera manager ready")
    
    # Video writing
    print("🎬 Setting up video writer...")
    raw_dir = config.processing.storage_path / "raw_footage"
    video_writer = VideoWriter(
        raw_dir, 
        config.capture.fps, 
        config.capture.resolution
    )
    print("✅ Video writer ready")
    
    # Sync service
    print("🔄 Setting up sync service...")
    sync_service = FileSyncService(
        config.sync.processing_server_host,
        config.sync.processing_server_port,
        config.sync.upload_timeout_seconds
    )
    print("✅ Sync service ready")
    
    # Main capture service
    print("🚀 Setting up capture service...")
    capture_service = CaptureService(
        config.capture,
        config.motion,
        camera_manager,
        motion_detector,
        video_writer,
        sync_service,
        video_repo
    )
    print("✅ Capture service ready")
    
    return capture_service, sync_service

def setup_scheduler(capture_service, config):
    """Setup scheduled tasks"""
    print("📅 Setting up scheduler...")
    
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
    print("✅ Scheduler started")

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
    
    try:
        # Load configuration
        print("📋 Loading configuration...")
        config = load_capture_config()
        print(f"✅ Config loaded - Stream: {config.capture.stream_url}")
        print(f"📁 Storage: {config.processing.storage_path}")
        
        # Setup services
        capture_service, sync_service = setup_services(config)
        
        # Setup scheduler
        setup_scheduler(capture_service, config)
        
        # Start capture
        print("🎬 Starting video capture...")
        capture_service.start_capture()
        print("✅ Capture started")
        
        # Start web interface
        print("🌐 Starting web interface...")
        app = create_capture_app(capture_service, sync_service, config)
        
        print(f"✅ System ready! Web interface: http://0.0.0.0:{config.web.capture_port}")
        print("🎯 Waiting for motion to trigger recording...")
        
        app.run(
            host=config.web.host,
            port=config.web.capture_port,
            threaded=True,
            debug=False
        )
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        if 'capture_service' in locals():
            capture_service.stop_capture()
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()