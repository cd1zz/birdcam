"""
Auth route handlers extracted from web/routes/auth_routes.py
These are standalone functions that can be imported by admin_routes.py
"""
from flask import request, jsonify, g
from core.models import UserRole
from web.utils.auth_utils import get_auth_service
import logging

logger = logging.getLogger(__name__)

def list_users_handler():
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

def create_user_handler():
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

def update_user_handler(user_id: int):
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
            # Pass the current admin's username for audit logging
            if not auth_service.update_role(user_id, role, changed_by=g.user.username):
                return jsonify({'error': 'Cannot update role (possibly last admin)'}), 400
        except ValueError:
            return jsonify({'error': f'Invalid role: {data["role"]}'}), 400
    
    return jsonify({'message': 'User updated successfully'})

def delete_user_handler(user_id: int):
    """Deactivate user (admin only)."""
    # Prevent self-deactivation
    if g.user.id == user_id:
        return jsonify({'error': 'Cannot deactivate your own account'}), 400
    
    auth_service = get_auth_service()
    
    # Pass the current admin's username for audit logging
    if not auth_service.deactivate_user(user_id, deactivated_by=g.user.username):
        return jsonify({'error': 'Cannot deactivate user (possibly last admin or not found)'}), 400
    
    return jsonify({'message': 'User deactivated successfully'})