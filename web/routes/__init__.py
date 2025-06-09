# web/routes/__init__.py
"""
Web routes for bird detection system
"""

from .capture_routes import create_capture_routes
from .processing_routes import create_processing_routes

__all__ = ['create_capture_routes', 'create_processing_routes']