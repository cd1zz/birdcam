# web/app.py
"""
Flask Application Factory
"""
from flask import Flask
from flask_cors import CORS
from config.settings import WebConfig

def create_capture_app(capture_services, sync_service, config):
    """Create Flask app for Pi capture system"""
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = config.web.max_content_length
    app.config['DATABASE_PATH'] = config.database.path
    
    if config.web.cors_enabled:
        CORS(app)
    
    # Import and register routes
    from web.routes.capture_routes import create_capture_routes
    
    create_capture_routes(app, capture_services, sync_service, {})
    
    return app

def create_processing_app(processing_service, video_repo, detection_repo, config):
    """Create Flask app for processing server"""
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = config.web.max_content_length
    app.config['DATABASE_PATH'] = config.database.path
    
    if config.web.cors_enabled:
        CORS(app)
    
    # Import and register routes
    from web.routes.processing_routes import create_processing_routes
    from web.routes.auth_routes import auth_bp
    from web.routes.setup_routes import setup_bp
    from web.routes.pi_proxy_routes import create_pi_proxy_routes
    from web.routes.log_routes import log_routes
    
    create_processing_routes(app, processing_service, video_repo, detection_repo, config)
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(setup_bp, url_prefix='/api/setup')
    app.register_blueprint(log_routes)
    
    # Add Pi proxy routes for secure camera access
    create_pi_proxy_routes(app, config)
    
    # Initialize user table
    from database.connection import DatabaseManager
    from database.repositories.user_repository import UserRepository
    db_manager = DatabaseManager(config.database.path)
    user_repo = UserRepository(db_manager)
    user_repo.create_table()
    
    return app
