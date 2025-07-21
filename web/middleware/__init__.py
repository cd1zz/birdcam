# web/middleware/__init__.py
"""
Middleware for the BirdCam web application
"""
from .auth import require_auth, require_admin
from .ip_restriction import require_internal_network

__all__ = [
    'require_auth',
    'require_admin', 
    'require_internal_network'
]