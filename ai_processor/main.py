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
