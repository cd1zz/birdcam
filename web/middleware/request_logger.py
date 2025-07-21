import logging
import logging.handlers
import time
from datetime import datetime
from flask import Flask, request, g
from werkzeug.exceptions import HTTPException
import socket

# Create logger for access logs
access_logger = logging.getLogger('birdcam.access')
access_logger.setLevel(logging.INFO)

# Configure syslog handler
syslog_handler = logging.handlers.SysLogHandler(
    address='/dev/log',  # Unix socket for local syslog
    facility=logging.handlers.SysLogHandler.LOG_LOCAL0
)

# Set formatter for Combined Log Format with logger name
# Format: logger_name: remote_addr - remote_user [timestamp] "request_line" status_code response_size "referer" "user_agent"
formatter = logging.Formatter(
    '%(name)s: %(message)s',
    datefmt='%d/%b/%Y:%H:%M:%S %z'
)
syslog_handler.setFormatter(formatter)

# Add handler to logger
access_logger.addHandler(syslog_handler)

def setup_request_logging(app: Flask):
    """Setup request logging middleware for Flask app"""
    
    @app.before_request
    def before_request():
        g.start_time = time.time()
    
    @app.after_request
    def after_request(response):
        # Skip logging for static files and health checks if desired
        if request.path.startswith('/static') or request.path == '/health':
            return response
            
        # Calculate request duration
        duration = time.time() - g.start_time
        
        # Get remote address (handle proxies)
        remote_addr = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ',' in remote_addr:
            remote_addr = remote_addr.split(',')[0].strip()
        
        # Get authenticated user from token if available
        remote_user = '-'
        if hasattr(g, 'current_user') and g.current_user:
            remote_user = g.current_user.get('username', '-')
        
        # Format timestamp
        timestamp = datetime.now().strftime('%d/%b/%Y:%H:%M:%S +0000')
        
        # Build request line
        request_line = f"{request.method} {request.full_path if request.query_string else request.path} {request.environ.get('SERVER_PROTOCOL', 'HTTP/1.1')}"
        
        # Get response size
        response_size = response.headers.get('Content-Length', '-')
        
        # Get referer and user agent
        referer = request.headers.get('Referer', '-')
        user_agent = request.headers.get('User-Agent', '-')
        
        # Build log message in Combined Log Format
        log_message = f'{remote_addr} - {remote_user} [{timestamp}] "{request_line}" {response.status_code} {response_size} "{referer}" "{user_agent}"'
        
        # Add request duration as extra field (common extension)
        log_message += f' {duration:.3f}s'
        
        # Log to syslog
        access_logger.info(log_message)
        
        return response
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        # Log errors as well
        if isinstance(e, HTTPException):
            status_code = e.code
        else:
            status_code = 500
            
        remote_addr = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ',' in remote_addr:
            remote_addr = remote_addr.split(',')[0].strip()
            
        timestamp = datetime.now().strftime('%d/%b/%Y:%H:%M:%S +0000')
        request_line = f"{request.method} {request.full_path if request.query_string else request.path} {request.environ.get('SERVER_PROTOCOL', 'HTTP/1.1')}"
        
        log_message = f'{remote_addr} - - [{timestamp}] "{request_line}" {status_code} - "-" "-"'
        access_logger.info(log_message)
        
        # Re-raise the exception for normal Flask error handling
        raise e