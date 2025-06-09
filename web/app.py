# web/app.py
"""
Flask Application Factory
"""
from flask import Flask
from flask_cors import CORS
from config.settings import WebConfig

def create_capture_app(capture_service, sync_service, config):
    """Create Flask app for Pi capture system"""
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = config.web.max_content_length
    
    if config.web.cors_enabled:
        CORS(app)
    
    # Import and register routes
    from web.routes.capture_routes import create_capture_routes
    create_capture_routes(app, capture_service, sync_service)
    
    return app

def create_processing_app(processing_service, video_repo, detection_repo, config):
    """Create Flask app for processing server"""
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = config.web.max_content_length
    
    if config.web.cors_enabled:
        CORS(app)
    
    # Import and register routes
    from web.routes.processing_routes import create_processing_routes
    create_processing_routes(app, processing_service, video_repo, detection_repo, config)
    
    return app
