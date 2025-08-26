# web/app.py
"""
Flask Application Factory
"""
from flask import Flask
from flask_cors import CORS

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
    app.config['SECRET_KEY'] = config.security.secret_key
    
    if config.web.cors_enabled:
        CORS(app)
    
    # Import and register routes
    from web.routes.processing_routes import create_processing_routes
    from web.routes.auth_routes import auth_bp
    from web.routes.setup_routes import setup_bp
    from web.routes.pi_proxy_routes import create_pi_proxy_routes
    from web.routes.log_routes import log_routes
    from web.routes.registration_routes import create_registration_routes
    from web.routes.security_routes import security_bp
    from web.admin_routes import admin_bp
    
    # Initialize database
    from database.connection import DatabaseManager
    from database.repositories.user_repository import UserRepository
    from database.repositories.registration_repository import RegistrationRepository
    db_manager = DatabaseManager(config.database.path)
    user_repo = UserRepository(db_manager)
    registration_repo = RegistrationRepository(db_manager)
    
    # Create tables
    user_repo.create_table()
    registration_repo.create_table()
    
    # Initialize services
    from services.auth_service import AuthService
    from services.email_service import EmailService
    from services.registration_service import RegistrationService
    
    auth_service = AuthService(user_repo)
    email_service = EmailService(app)
    registration_service = RegistrationService(user_repo, registration_repo, auth_service, email_service)
    
    # Register routes
    create_processing_routes(app, processing_service, video_repo, detection_repo, config)
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(setup_bp, url_prefix='/api/setup')
    app.register_blueprint(log_routes)
    
    # Register admin blueprint (includes user management routes)
    app.register_blueprint(admin_bp)
    
    # Register security routes
    app.register_blueprint(security_bp, url_prefix='/api/security')
    
    # Register registration routes
    registration_bp = create_registration_routes(registration_service, email_service)
    app.register_blueprint(registration_bp)
    
    # Add Pi proxy routes for secure camera access
    create_pi_proxy_routes(app, config)
    
    return app
