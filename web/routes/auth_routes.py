# web/routes/auth_routes.py
from flask import Blueprint, request, jsonify, g
from web.middleware.auth import require_auth
from web.utils.auth_utils import get_auth_service
import logging
import uuid

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

@auth_bp.before_request
def before_request():
    """Set request ID for correlation"""
    g.request_id = str(uuid.uuid4())

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