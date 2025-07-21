# web/middleware/auth.py
from functools import wraps
from flask import request, jsonify, g
from typing import Optional, Callable
from core.models import User, UserRole
from services.auth_service import AuthService
from database.repositories.user_repository import UserRepository
from database.connection import DatabaseManager
import logging

logger = logging.getLogger(__name__)

def get_auth_service(db_path) -> AuthService:
    """Create auth service instance."""
    db_manager = DatabaseManager(db_path)
    user_repository = UserRepository(db_manager)
    return AuthService(user_repository)

def get_token_from_header() -> Optional[str]:
    """Extract JWT token from Authorization header."""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return None
    
    # Bearer token format: "Bearer <token>"
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None
    
    return parts[1]

def get_token_from_request() -> Optional[str]:
    """Extract JWT token from header or query parameter."""
    # First try header
    token = get_token_from_header()
    if token:
        return token
    
    # Then try query parameter (for streaming endpoints)
    token = request.args.get('token')
    if token:
        # Clean up token in case of malformed query string
        # Remove any trailing query parameters that got attached
        if '?' in token:
            token = token.split('?')[0]
        return token.strip()
    
    return None

def require_auth(f: Callable) -> Callable:
    """Decorator to require authentication for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_token_from_header()
        
        if not token:
            return jsonify({'error': 'Missing authentication token'}), 401
        
        # Get auth service (assumes Flask app has db_path in config)
        from flask import current_app
        auth_service = get_auth_service(current_app.config['DATABASE_PATH'])
        
        # Validate token
        user = auth_service.validate_token(token)
        if not user:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Store user in g for access in route
        g.user = user
        
        return f(*args, **kwargs)
    
    return decorated_function

def require_role(role: UserRole) -> Callable:
    """Decorator to require a specific role for a route."""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            if g.user.role != role and g.user.role != UserRole.ADMIN:
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator

def require_admin(f: Callable) -> Callable:
    """Decorator to require admin role for a route."""
    return require_role(UserRole.ADMIN)(f)

def optional_auth(f: Callable) -> Callable:
    """Decorator that checks for authentication but doesn't require it."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_token_from_header()
        
        if token:
            # Get auth service
            from flask import current_app
            auth_service = get_auth_service(current_app.config['DATABASE_PATH'])
            
            # Validate token
            user = auth_service.validate_token(token)
            g.user = user  # Will be None if invalid
        else:
            g.user = None
        
        return f(*args, **kwargs)
    
    return decorated_function

def require_auth_with_query(f: Callable) -> Callable:
    """Decorator to require authentication, accepting token from header or query param.
    Used for streaming endpoints where browser can't send headers."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_token_from_request()  # Uses both header and query param
        
        if not token:
            return jsonify({'error': 'Missing authentication token'}), 401
        
        # Get auth service (assumes Flask app has db_path in config)
        from flask import current_app
        auth_service = get_auth_service(current_app.config['DATABASE_PATH'])
        
        # Validate token
        try:
            user = auth_service.validate_token(token)
            if not user:
                logger.warning(f"Token validation failed for streaming endpoint: {request.path}")
                return jsonify({'error': 'Invalid or expired token'}), 401
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            return jsonify({'error': 'Token validation error'}), 401
        
        # Store user in g for access in route
        g.user = user
        
        return f(*args, **kwargs)
    
    return decorated_function