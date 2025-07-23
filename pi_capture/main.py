#!/usr/bin/env python3
"""
Raspberry Pi Capture System Entry Point

Manages video capture from multiple cameras with motion detection,
file synchronization, and web interface for monitoring and configuration.
"""
import schedule
import threading
import time
import os
from pathlib import Path

from config.settings import load_all_capture_configs
from database.connection import DatabaseManager
from database.repositories.video_repository import VideoRepository
from database.repositories.settings_repository import SettingsRepository
from services.motion_detector import MotionDetector
from services.camera_manager import CameraManager, print_detected_cameras
from services.video_writer import VideoWriter
from services.file_sync import FileSyncService
from services.capture_service import CaptureService
from utils.capture_logger import logger
# Core service imports
from web.app import create_capture_app


def setup_services(config, force_opencv=False):
    """Initialize all services with settings persistence"""
    logger.setup("Setting up services...")
    
    # Database
    logger.database("Initializing database...")
    db_manager = DatabaseManager(config.database.path)
    video_repo = VideoRepository(db_manager)
    settings_repo = SettingsRepository(db_manager)
    
    # Create tables
    video_repo.create_table()
    settings_repo.create_table()
    
    # Ensure database schema is up to date
    settings_repo.migrate_settings_table()
    
    logger.ok("Database ready")
    
    # Load saved motion settings
    logger.config("Loading saved motion settings...")
    saved_settings = settings_repo.load_motion_settings()
    if saved_settings:
        # Apply saved settings to config
        config.motion.region = (
            saved_settings['region'].x1, saved_settings['region'].y1,
            saved_settings['region'].x2, saved_settings['region'].y2
        )
        config.motion.threshold = saved_settings['motion_threshold']
        config.motion.min_contour_area = saved_settings['min_contour_area']
        config.motion.motion_timeout_seconds = saved_settings['motion_timeout_seconds']
        logger.ok("Loaded saved settings", region=config.motion.region,
                 threshold=config.motion.threshold, timeout_seconds=config.motion.motion_timeout_seconds)
    else:
        logger.info("No saved settings found, using defaults")
    
    # Core services
    logger.setup("Setting up motion detector...")
    motion_detector = MotionDetector(config.motion)
    logger.ok("Motion detector ready")

    logger.setup("Setting up camera manager...")
    camera_manager = CameraManager(config.capture, force_opencv=force_opencv)
    logger.ok("Camera manager ready")

    # Video writing
    logger.setup("Setting up video writer...")
    raw_dir = config.processing.storage_path / "raw_footage"
    video_writer = VideoWriter(
        raw_dir,
        config.capture.fps,
        config.capture.resolution,
        config.capture.camera_id
    )
    logger.ok("Video writer ready")

    # Sync service
    logger.setup("Setting up sync service...")
    sync_service = FileSyncService(
        config.sync.processing_server_host,
        config.sync.processing_server_port,
        config.sync.upload_timeout_seconds,
        config.security.secret_key
    )
    logger.ok("Sync service ready")

    # Main capture service
    logger.setup("Setting up capture service...")
    capture_service = CaptureService(
        config.capture,
        config.motion,
        camera_manager,
        motion_detector,
        video_writer,
        sync_service,
        video_repo
    )
    logger.ok("Capture service ready")

    return capture_service, sync_service, settings_repo


def setup_scheduler(capture_service, config):
    """Setup scheduled tasks"""
    logger.scheduler("Setting up scheduler...")
    
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
    logger.ok("Scheduler started")

def cleanup_old_files(storage_path: Path, days_to_keep: int):
    """Clean up old files"""
    from datetime import datetime, timedelta
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    
    synced_dir = storage_path / "synced"
    if synced_dir.exists():
        for file_path in synced_dir.glob("*.mp4"):
            if datetime.fromtimestamp(file_path.stat().st_mtime) < cutoff_date:
                file_path.unlink()
                logger.cleanup(f"Cleaned up: {file_path.name}")

def create_unified_app(capture_services, sync_service, settings_repos, config):
    """Create Flask app with unified dashboard"""
    from flask import Flask
    from flask_cors import CORS
    
    app = Flask(__name__, template_folder='../web/templates', static_folder='../web/static')
    app.config['MAX_CONTENT_LENGTH'] = config.web.max_content_length
    
    if config.web.cors_enabled:
        CORS(app)
    
    # Import and register routes with settings repo
    from web.routes.capture_routes import create_capture_routes
    create_capture_routes(app, capture_services, sync_service, settings_repos)
    
    return app

def main():
    logger.info("Starting Pi Capture System with Unified Dashboard...")

    # Inform user about detected cameras before loading configs
    logger.camera("Detecting cameras...")
    print_detected_cameras()

    try:
        # Load configuration for all cameras
        logger.config("Loading configuration...")
        configs = load_all_capture_configs()
        logger.ok(f"Loaded {len(configs)} camera configuration(s)")
        

        capture_services = {}
        sync_service = None
        settings_repos = {}
        
        # Check for force OpenCV mode
        force_opencv = os.getenv("FORCE_OPENCV", "false").lower() == "true"
        if force_opencv:
            logger.info("FORCE_OPENCV mode enabled - using OpenCV for all cameras")

        for cfg in configs:
            logger.storage(f"Storage for camera {cfg.capture.camera_id}", path=cfg.processing.storage_path)
            logger.camera(f"Camera {cfg.capture.camera_id} configured as: {cfg.capture.camera_type}")

            cs, sync, settings = setup_services(cfg, force_opencv=force_opencv)
            capture_services[cfg.capture.camera_id] = cs
            settings_repos[cfg.capture.camera_id] = settings
            if sync_service is None:
                sync_service = sync

            setup_scheduler(cs, cfg)

        if not capture_services:
            raise RuntimeError("No camera configurations found")
        
        # Set up active-passive relationships
        logger.setup("Setting up active-passive camera relationships...")
        active_service = capture_services.get(0)  # Camera 0 is active
        if active_service:
            for camera_id, service in capture_services.items():
                if camera_id != 0:  # All other cameras are passive
                    active_service.set_passive_camera(service)
                    logger.link(f"Linked active camera 0 to passive camera {camera_id}")
        else:
            logger.warning("No active camera (camera 0) found - using single camera mode")
        
        # Start all capture services
        logger.capture("Starting video capture for all cameras...")
        for camera_id, cs in capture_services.items():
            cs.start_capture()
            logger.ok(f"Capture started for camera {camera_id}")

        # Start web interface with unified dashboard using first config
        logger.web("Starting unified dashboard...")
        app = create_unified_app(capture_services, sync_service, settings_repos, configs[0])
        
        logger.ok("Unified Dashboard ready!")
        logger.web(f"Access at: http://0.0.0.0:{configs[0].web.capture_port}")
        logger.info("This dashboard shows both Pi capture AND AI processing status")
        logger.config("Motion settings will be saved and restored on restart")
        if len(capture_services) > 1:
            logger.link("Active-passive setup: Camera 0 detects motion, all cameras record")
        else:
            logger.camera("Single camera mode active")
        
        app.run(
            host=configs[0].web.host,
            port=configs[0].web.capture_port,
            threaded=True,
            debug=False
        )
    except KeyboardInterrupt:
        logger.stop("Shutting down...")
        for cs in capture_services.values():
            cs.stop_capture()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()