# utils/security_logger.py
import logging
import logging.handlers
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from flask import request, g

# Create logger for security audit events
security_logger = logging.getLogger('birdcam.security.audit')
security_logger.setLevel(logging.INFO)

# Configure syslog handler
syslog_handler = logging.handlers.SysLogHandler(
    address='/dev/log',
    facility=logging.handlers.SysLogHandler.LOG_LOCAL0
)

# Use a JSON formatter for structured logging
class SecurityJSONFormatter(logging.Formatter):
    def format(self, record):
        # Get the log data from the record
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'severity': record.levelname,
            'logger': record.name,
            'event_type': getattr(record, 'event_type', 'unknown'),
        }
        
        # Add all custom fields from the record
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName', 
                          'levelname', 'levelno', 'lineno', 'module', 'msecs', 
                          'pathname', 'process', 'processName', 'relativeCreated', 
                          'thread', 'threadName', 'getMessage', 'event_type']:
                log_data[key] = value
                
        return json.dumps(log_data)

# Set JSON formatter
json_formatter = SecurityJSONFormatter()
syslog_handler.setFormatter(json_formatter)

# Add handler to logger
security_logger.addHandler(syslog_handler)

def get_request_context() -> Dict[str, Any]:
    """Extract request context for security logging"""
    context = {}
    
    if request:
        # Get IP address (handle proxies)
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ',' in ip_address:
            ip_address = ip_address.split(',')[0].strip()
        context['ip_address'] = ip_address
        
        # Get user agent
        context['user_agent'] = request.headers.get('User-Agent', 'unknown')
        
        # Get request ID if available, otherwise generate one
        if hasattr(g, 'request_id'):
            context['request_id'] = g.request_id
        else:
            context['request_id'] = str(uuid.uuid4())
            
        # Get request method and path
        context['request_method'] = request.method
        context['request_path'] = request.path
        
    return context

def log_auth_failed(username: str, reason: str, extra_data: Optional[Dict[str, Any]] = None):
    """Log failed authentication attempt"""
    log_data = {
        'event_type': 'auth_failed',
        'username': username,
        'failure_reason': reason,
        **get_request_context()
    }
    
    if extra_data:
        log_data.update(extra_data)
        
    security_logger.warning('Authentication failed', extra=log_data)

def log_auth_success(username: str, extra_data: Optional[Dict[str, Any]] = None):
    """Log successful authentication"""
    log_data = {
        'event_type': 'auth_success',
        'username': username,
        **get_request_context()
    }
    
    if extra_data:
        log_data.update(extra_data)
        
    security_logger.info('Authentication successful', extra=log_data)

def log_password_changed(username: str, changed_by: Optional[str] = None):
    """Log password change event"""
    log_data = {
        'event_type': 'password_changed',
        'username': username,
        'changed_by': changed_by or username,  # Self if not specified
        **get_request_context()
    }
    
    security_logger.info('Password changed', extra=log_data)

def log_token_refresh_failed(reason: str, extra_data: Optional[Dict[str, Any]] = None):
    """Log failed token refresh attempt"""
    log_data = {
        'event_type': 'token_refresh_failed',
        'failure_reason': reason,
        **get_request_context()
    }
    
    if extra_data:
        log_data.update(extra_data)
        
    security_logger.warning('Token refresh failed', extra=log_data)

def log_role_changed(target_username: str, new_role: str, changed_by: str):
    """Log role change event"""
    log_data = {
        'event_type': 'role_changed',
        'target_username': target_username,
        'new_role': new_role,
        'changed_by': changed_by,
        **get_request_context()
    }
    
    security_logger.info('User role changed', extra=log_data)

def log_user_deactivated(username: str, deactivated_by: str):
    """Log user deactivation event"""
    log_data = {
        'event_type': 'user_deactivated',
        'username': username,
        'deactivated_by': deactivated_by,
        **get_request_context()
    }
    
    security_logger.info('User deactivated', extra=log_data)

def log_suspicious_activity(activity_type: str, details: Dict[str, Any]):
    """Log suspicious activity for external monitoring"""
    log_data = {
        'event_type': 'suspicious_activity',
        'activity_type': activity_type,
        **details,
        **get_request_context()
    }
    
    security_logger.warning('Suspicious activity detected', extra=log_data)