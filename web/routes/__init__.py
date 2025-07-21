# web/routes/__init__.py
"""
Web routes for bird detection system
"""

# Always available
from .capture_routes import create_capture_routes

# Only import processing routes if auth dependencies are available
try:
    from .processing_routes import create_processing_routes
    __all__ = ['create_capture_routes', 'create_processing_routes']
except ImportError:
    # Processing routes not available on Pi capture system
    __all__ = ['create_capture_routes']