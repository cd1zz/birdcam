# pi_capture/main.py - UPDATED WITH SETTINGS PERSISTENCE
#!/usr/bin/env python3
"""
Raspberry Pi Capture System Entry Point with Settings Persistence
"""
import schedule
import threading
import time
from pathlib import Path

from config.settings import load_capture_config
from database.connection import DatabaseManager
from database.repositories.video_repository import VideoRepository
from database.repositories.settings_repository import SettingsRepository
from services.motion_detector import MotionDetector
from services.camera_manager import CameraManager
from services.video_writer import VideoWriter
from services.file_sync import FileSyncService
from services.capture_service import CaptureService
from web.app import create_capture_app


def setup_services(config):
    """Initialize all services with settings persistence"""
    print("🔧 Setting up services...")
    
    # Database
    print("📊 Initializing database...")
    db_manager = DatabaseManager(config.database.path)
    video_repo = VideoRepository(db_manager)
    settings_repo = SettingsRepository(db_manager)
    
    # Create tables
    video_repo.create_table()
    settings_repo.create_table()
    
    # ADDED: Migrate existing database if needed
    settings_repo.migrate_settings_table()
    
    print("✅ Database ready")
    
    # Load saved motion settings
    print("⚙️ Loading saved motion settings...")
    saved_settings = settings_repo.load_motion_settings()
    if saved_settings:
        # Apply saved settings to config
        config.motion.region = (
            saved_settings['region'].x1, saved_settings['region'].y1,
            saved_settings['region'].x2, saved_settings['region'].y2
        )
        config.motion.threshold = saved_settings['motion_threshold']
        config.motion.min_contour_area = saved_settings['min_contour_area']
        config.motion.motion_timeout_seconds = saved_settings['motion_timeout_seconds']  # ADDED
        print(f"✅ Loaded saved settings: region={config.motion.region}, "
              f"threshold={config.motion.threshold}, timeout={config.motion.motion_timeout_seconds}s")
    else:
        print("📋 No saved settings found, using defaults")
    
    # Rest of the function remains the same...
    print("🎯 Setting up motion detector...")
    motion_detector = MotionDetector(config.motion)
    print("✅ Motion detector ready")
    

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

def create_unified_app(capture_service, sync_service, settings_repo, config):
    """Create Flask app with unified dashboard"""
    from flask import Flask
    from flask_cors import CORS
    
    app = Flask(__name__, template_folder='../web/templates', static_folder='../web/static')
    app.config['MAX_CONTENT_LENGTH'] = config.web.max_content_length
    
    if config.web.cors_enabled:
        CORS(app)
    
    # Import and register routes with settings repo
    from web.routes.capture_routes import create_capture_routes
    create_capture_routes(app, capture_service, sync_service, settings_repo)
    
    return app

def main():
    print("🚀 Starting Pi Capture System with Unified Dashboard...")
    
    try:
        # Load configuration
        print("📋 Loading configuration...")
        config = load_capture_config()
        print(f"✅ Config loaded - Stream: {config.capture.stream_url}")
        print(f"📁 Storage: {config.processing.storage_path}")
        
        # Setup services
        capture_service, sync_service, settings_repo = setup_services(config)
        
        # Setup scheduler
        setup_scheduler(capture_service, config)
        
        # Start capture
        print("🎬 Starting video capture...")
        capture_service.start_capture()
        print("✅ Capture started")
        
        # Start web interface with unified dashboard
        print("🌐 Starting unified dashboard...")
        app = create_unified_app(capture_service, sync_service, settings_repo, config)
        
        print(f"✅ Unified Dashboard ready!")
        print(f"🌐 Access at: http://0.0.0.0:{config.web.capture_port}")
        print("🎯 This dashboard shows both Pi capture AND AI processing status")
        print("⚙️ Motion settings will be saved and restored on restart")
        
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