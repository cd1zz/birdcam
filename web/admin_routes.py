"""
Centralized admin API routes
All admin-only endpoints are organized under /api/admin/*
"""
from flask import Blueprint, request, jsonify, current_app
from core.models import User, UserRole
from web.middleware import require_auth
from web.middleware.decorators import require_admin_internal
from utils.capture_logger import logger
import json
import os

# Import route handlers from other modules
from web.handlers.auth_handlers import list_users_handler, create_user_handler, update_user_handler, delete_user_handler
from web.handlers.log_handlers import get_logs_handler, get_log_files_handler, get_capture_logs_handler, download_logs_handler, clear_logs_handler

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

# User Management Routes
@admin_bp.route('/users', methods=['GET'])
@require_admin_internal
def list_users():
    """List all users (admin only)"""
    return list_users_handler()

@admin_bp.route('/users', methods=['POST'])
@require_admin_internal
def create_user():
    """Create a new user (admin only)"""
    return create_user_handler()

@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@require_admin_internal
def update_user(user_id):
    """Update user details (admin only)"""
    return update_user_handler(user_id)

@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@require_admin_internal
def delete_user(user_id):
    """Deactivate a user (admin only)"""
    return delete_user_handler(user_id)

# System Logs Routes
@admin_bp.route('/logs', methods=['GET'])
@require_admin_internal
def get_logs():
    """Get recent logs from the processing server"""
    return get_logs_handler()

@admin_bp.route('/logs/files', methods=['GET'])
@require_admin_internal
def get_log_files():
    """Get list of available log files"""
    return get_log_files_handler()

@admin_bp.route('/logs/capture', methods=['GET'])
@require_admin_internal
def get_capture_logs():
    """Get recent logs from all capture services"""
    return get_capture_logs_handler()

@admin_bp.route('/logs/download/<filename>', methods=['GET'])
@require_admin_internal
def download_log(filename):
    """Download a specific log file"""
    return download_logs_handler(filename)

@admin_bp.route('/logs/clear', methods=['POST'])
@require_admin_internal
def clear_logs():
    """Clear log files (admin only)"""
    return clear_logs_handler()


# System Settings Routes
@admin_bp.route('/settings/system', methods=['GET'])
@require_auth
def get_system_settings():
    """Get system configuration settings"""
    try:
        config = current_app.config
        settings = {
            'detection': {
                'confidence_threshold': config.get('CONFIDENCE_THRESHOLD', 0.5),
                'detected_classes': config.get('DETECTED_CLASSES', [])
            },
            'storage': {
                'retention_days_detections': config.get('RETENTION_DAYS_DETECTIONS', 30),
                'retention_days_no_detections': config.get('RETENTION_DAYS_NO_DETECTIONS', 7),
                'max_storage_gb': config.get('MAX_STORAGE_GB', 100)
            },
            'sync': {
                'sync_interval_minutes': config.get('SYNC_INTERVAL_MINUTES', 15),
                'batch_size': config.get('BATCH_SIZE', 10)
            }
        }
        return jsonify(settings), 200
    except Exception as e:
        logger.error(f"Failed to get system settings: {e}")
        return jsonify({'error': 'Failed to retrieve settings'}), 500

@admin_bp.route('/settings/system', methods=['POST'])
@require_admin_internal
def update_system_settings():
    """Update system configuration settings"""
    try:
        data = request.json
        
        # Update .env file with new settings
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        
        # Read current .env content
        env_vars = {}
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        env_vars[key] = value
        
        # Update values from request
        if 'detection' in data:
            if 'confidence_threshold' in data['detection']:
                env_vars['CONFIDENCE_THRESHOLD'] = str(data['detection']['confidence_threshold'])
            if 'detected_classes' in data['detection']:
                env_vars['DETECTED_CLASSES'] = ','.join(data['detection']['detected_classes'])
        
        if 'storage' in data:
            if 'retention_days_detections' in data['storage']:
                env_vars['RETENTION_DAYS_DETECTIONS'] = str(data['storage']['retention_days_detections'])
            if 'retention_days_no_detections' in data['storage']:
                env_vars['RETENTION_DAYS_NO_DETECTIONS'] = str(data['storage']['retention_days_no_detections'])
            if 'max_storage_gb' in data['storage']:
                env_vars['MAX_STORAGE_GB'] = str(data['storage']['max_storage_gb'])
        
        if 'sync' in data:
            if 'sync_interval_minutes' in data['sync']:
                env_vars['SYNC_INTERVAL_MINUTES'] = str(data['sync']['sync_interval_minutes'])
            if 'batch_size' in data['sync']:
                env_vars['BATCH_SIZE'] = str(data['sync']['batch_size'])
        
        # Write updated .env file
        with open(env_path, 'w') as f:
            for key, value in sorted(env_vars.items()):
                f.write(f"{key}={value}\n")
        
        logger.info("System settings updated successfully")
        return jsonify({'message': 'Settings updated successfully. Restart services for changes to take effect.'}), 200
        
    except Exception as e:
        logger.error(f"Failed to update system settings: {e}")
        return jsonify({'error': 'Failed to update settings'}), 500


# System Status/Stats Routes
@admin_bp.route('/stats/system', methods=['GET'])
@require_admin_internal
def get_system_stats():
    """Get system statistics (CPU, memory, disk usage)"""
    try:
        import psutil
        
        # Get disk usage for the footage directory
        footage_path = current_app.config.get('FOOTAGE_PATH', '/var/lib/birdcam/footage')
        disk_usage = psutil.disk_usage(footage_path)
        
        stats = {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory': {
                'percent': psutil.virtual_memory().percent,
                'used_gb': round(psutil.virtual_memory().used / (1024**3), 2),
                'total_gb': round(psutil.virtual_memory().total / (1024**3), 2)
            },
            'disk': {
                'percent': disk_usage.percent,
                'used_gb': round(disk_usage.used / (1024**3), 2),
                'total_gb': round(disk_usage.total / (1024**3), 2),
                'free_gb': round(disk_usage.free / (1024**3), 2)
            }
        }
        
        return jsonify(stats), 200
    except Exception as e:
        logger.error(f"Failed to get system stats: {e}")
        return jsonify({'error': 'Failed to get system statistics'}), 500

@admin_bp.route('/stats/cameras', methods=['GET'])
@require_auth
def get_camera_stats():
    """Get camera statistics"""
    try:
        # This would normally query the capture services
        # For now, return mock data
        stats = {
            'total_cameras': 0,
            'active_cameras': 0,
            'cameras': []
        }
        
        # TODO: Implement actual camera stats collection
        
        return jsonify(stats), 200
    except Exception as e:
        logger.error(f"Failed to get camera stats: {e}")
        return jsonify({'error': 'Failed to get camera statistics'}), 500