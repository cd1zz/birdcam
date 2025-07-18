# web/routes/setup_routes.py
"""
Initial setup routes for first-time configuration
"""
from flask import Blueprint, request, jsonify, current_app
from core.models import UserRole
from services.auth_service import AuthService
from database.repositories.user_repository import UserRepository
from database.connection import DatabaseManager
from web.middleware.ip_restriction import require_internal_network
import logging

logger = logging.getLogger(__name__)

setup_bp = Blueprint('setup', __name__)

def get_auth_service() -> AuthService:
    """Create auth service instance."""
    db_manager = DatabaseManager(current_app.config['DATABASE_PATH'])
    user_repository = UserRepository(db_manager)
    return AuthService(user_repository)

@setup_bp.route('/status', methods=['GET'])
def setup_status():
    """
    Check if initial setup is required.
    Public endpoint - no authentication required.
    """
    try:
        auth_service = get_auth_service()
        
        # Ensure user table exists
        auth_service.user_repository.create_table()
        
        # Check if any admin users exist
        admin_count = auth_service.user_repository.count_by_role(UserRole.ADMIN)
        
        return jsonify({
            'setup_required': admin_count == 0,
            'admin_exists': admin_count > 0
        })
    except Exception as e:
        logger.error(f"Error checking setup status: {e}")
        return jsonify({
            'error': 'Failed to check setup status',
            'message': str(e)
        }), 500

@setup_bp.route('/create-admin', methods=['POST'])
@require_internal_network
def create_first_admin():
    """
    Create the first admin user.
    Only works when no admin users exist.
    Restricted to internal network IPs only.
    """
    try:
        data = request.get_json()
        
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({'error': 'Username and password required'}), 400
        
        username = data['username'].strip()
        password = data['password']
        
        # Validate inputs
        if len(username) < 3:
            return jsonify({'error': 'Username must be at least 3 characters'}), 400
            
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        
        auth_service = get_auth_service()
        
        # Ensure user table exists
        auth_service.user_repository.create_table()
        
        # Check if any admin users already exist
        admin_count = auth_service.user_repository.count_by_role(UserRole.ADMIN)
        if admin_count > 0:
            return jsonify({
                'error': 'Setup already completed',
                'message': 'An admin user already exists. Please use the login page.'
            }), 403
        
        # Check if username already exists
        if auth_service.user_repository.get_by_username(username):
            return jsonify({'error': 'Username already exists'}), 409
        
        # Create the admin user
        user = auth_service.create_user(username, password, UserRole.ADMIN)
        
        if not user:
            return jsonify({'error': 'Failed to create admin user'}), 500
        
        # Generate tokens for immediate login
        result = auth_service.authenticate(username, password)
        if not result:
            return jsonify({'error': 'User created but authentication failed'}), 500
            
        user, access_token, refresh_token = result
        
        logger.info(f"First admin user '{username}' created successfully")
        
        return jsonify({
            'message': 'Admin user created successfully',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': {
                'id': user.id,
                'username': user.username,
                'role': user.role.value
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating first admin: {e}")
        return jsonify({
            'error': 'Failed to create admin user',
            'message': str(e)
        }), 500