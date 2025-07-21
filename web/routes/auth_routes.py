# web/routes/auth_routes.py
from flask import Blueprint, request, jsonify, current_app
from core.models import UserRole
from services.auth_service import AuthService
from database.repositories.user_repository import UserRepository
from database.connection import DatabaseManager
from web.middleware.auth import require_auth, require_admin, g
import logging

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

def get_auth_service() -> AuthService:
    """Create auth service instance."""
    db_manager = DatabaseManager(current_app.config['DATABASE_PATH'])
    user_repository = UserRepository(db_manager)
    return AuthService(user_repository)

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login endpoint."""
    data = request.get_json()
    
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Username and password required'}), 400
    
    auth_service = get_auth_service()
    result = auth_service.authenticate(data['username'], data['password'])
    
    if not result:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    user, access_token, refresh_token = result
    
    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': {
            'id': user.id,
            'username': user.username,
            'role': user.role.value,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'last_login': user.last_login.isoformat() if user.last_login else None
        }
    })

@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    """Refresh tokens endpoint."""
    data = request.get_json()
    
    if not data or 'refresh_token' not in data:
        return jsonify({'error': 'Refresh token required'}), 400
    
    auth_service = get_auth_service()
    result = auth_service.refresh_tokens(data['refresh_token'])
    
    if not result:
        return jsonify({'error': 'Invalid refresh token'}), 401
    
    access_token, refresh_token = result
    
    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token
    })

@auth_bp.route('/me', methods=['GET'])
@require_auth
def get_current_user():
    """Get current user info."""
    return jsonify({
        'id': g.user.id,
        'username': g.user.username,
        'role': g.user.role.value,
        'created_at': g.user.created_at.isoformat() if g.user.created_at else None,
        'last_login': g.user.last_login.isoformat() if g.user.last_login else None
    })

@auth_bp.route('/users', methods=['GET'])
@require_admin
def list_users():
    """List all users (admin only)."""
    auth_service = get_auth_service()
    users = auth_service.user_repository.get_all()
    
    return jsonify({
        'users': [{
            'id': user.id,
            'username': user.username,
            'role': user.role.value,
            'is_active': user.is_active,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'last_login': user.last_login.isoformat() if user.last_login else None
        } for user in users]
    })

@auth_bp.route('/users', methods=['POST'])
@require_admin
def create_user():
    """Create a new user (admin only)."""
    data = request.get_json()
    
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Username and password required'}), 400
    
    # Parse role
    role_str = data.get('role', 'viewer')
    try:
        role = UserRole(role_str)
    except ValueError:
        return jsonify({'error': f'Invalid role: {role_str}'}), 400
    
    auth_service = get_auth_service()
    user = auth_service.create_user(data['username'], data['password'], role)
    
    if not user:
        return jsonify({'error': 'Username already exists'}), 409
    
    return jsonify({
        'id': user.id,
        'username': user.username,
        'role': user.role.value,
        'created_at': user.created_at.isoformat() if user.created_at else None
    }), 201

@auth_bp.route('/users/<int:user_id>', methods=['PUT'])
@require_admin
def update_user(user_id: int):
    """Update user (admin only)."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    auth_service = get_auth_service()
    
    # Handle password update request
    if 'password' in data:
        if not auth_service.update_password(user_id, data['password']):
            return jsonify({'error': 'User not found'}), 404
    
    # Handle role update request
    if 'role' in data:
        try:
            role = UserRole(data['role'])
            if not auth_service.update_role(user_id, role):
                return jsonify({'error': 'Cannot update role (possibly last admin)'}), 400
        except ValueError:
            return jsonify({'error': f'Invalid role: {data["role"]}'}), 400
    
    return jsonify({'message': 'User updated successfully'})

@auth_bp.route('/users/<int:user_id>', methods=['DELETE'])
@require_admin
def deactivate_user(user_id: int):
    """Deactivate user (admin only)."""
    # Prevent self-deactivation
    if g.user.id == user_id:
        return jsonify({'error': 'Cannot deactivate your own account'}), 400
    
    auth_service = get_auth_service()
    
    if not auth_service.deactivate_user(user_id):
        return jsonify({'error': 'Cannot deactivate user (possibly last admin or not found)'}), 400
    
    return jsonify({'message': 'User deactivated successfully'})

@auth_bp.route('/change-password', methods=['POST'])
@require_auth
def change_password():
    """Change own password."""
    data = request.get_json()
    
    if not data or 'current_password' not in data or 'new_password' not in data:
        return jsonify({'error': 'Current and new passwords required'}), 400
    
    auth_service = get_auth_service()
    
    # Verify current password
    result = auth_service.authenticate(g.user.username, data['current_password'])
    if not result:
        return jsonify({'error': 'Current password is incorrect'}), 401
    
    # Update password
    if not auth_service.update_password(g.user.id, data['new_password']):
        return jsonify({'error': 'Failed to update password'}), 500
    
    return jsonify({'message': 'Password changed successfully'})