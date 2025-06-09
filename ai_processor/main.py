#!/usr/bin/env python3
"""
AI Processing Server Entry Point
"""
import schedule
import threading
import time
import sys
from pathlib import Path

from config.settings import load_processing_config
from database.connection import DatabaseManager
from database.repositories.video_repository import VideoRepository
from database.repositories.detection_repository import DetectionRepository
from services.ai_model_manager import AIModelManager
from services.processing_service import ProcessingService
from web.app import create_processing_app

def setup_services(config):
    """Initialize all services"""
    try:
        print("📊 Setting up database...")
        # Database
        db_manager = DatabaseManager(config.database.path)
        video_repo = VideoRepository(db_manager)
        detection_repo = DetectionRepository(db_manager)
        
        # Create tables
        video_repo.create_table()
        detection_repo.create_table()
        print("✅ Database initialized")
        
        print("🤖 Setting up AI model manager...")
        # AI services
        model_manager = AIModelManager(
            config.processing.model_name,
            config.processing.confidence_threshold
        )
        print("✅ AI model manager ready")
        
        print("⚙️ Setting up processing service...")
        # Processing service
        processing_service = ProcessingService(
            config.processing,
            model_manager,
            video_repo,
            detection_repo
        )
        print("✅ Processing service ready")
        
        return processing_service, video_repo, detection_repo
        
    except Exception as e:
        print(f"❌ Failed to setup services: {e}")
        raise

def setup_scheduler(processing_service, config):
    """Setup scheduled tasks"""
    try:
        print("📅 Setting up scheduler...")
        # Auto-process every 30 minutes
        schedule.every(30).minutes.do(processing_service.process_pending_videos)
        
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(60)
        
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        print("✅ Scheduler started")
        
    except Exception as e:
        print(f"❌ Failed to setup scheduler: {e}")
        raise

def main():
    print("🧠 Starting AI Processing Server...")
    
    try:
        # Load configuration
        print("📋 Loading configuration...")
        config = load_processing_config()
        print(f"✅ Configuration loaded - Storage: {config.processing.storage_path}")
        
        # Setup services
        processing_service, video_repo, detection_repo = setup_services(config)
        
        # Setup scheduler
        setup_scheduler(processing_service, config)
        
        # Start web interface
        print("🌐 Starting web interface...")
        app = create_processing_app(processing_service, video_repo, detection_repo, config)
        
        print(f"✅ Processing server ready!")
        print(f"🌐 Web interface: http://0.0.0.0:{config.web.processing_port}")
        print(f"💾 Storage path: {config.processing.storage_path}")
        print(f"🤖 Model: {config.processing.model_name}")
        print("📡 Waiting for videos to process...")
        
        app.run(
            host=config.web.host,
            port=config.web.processing_port,
            threaded=True,
            debug=False
        )
        
    except KeyboardInterrupt:
        print("\n🛑 Shutting down gracefully...")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        print("💡 Check your configuration and dependencies")
        sys.exit(1)

if __name__ == '__main__':
    main()