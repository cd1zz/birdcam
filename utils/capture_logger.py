"""
Logging utilities for Pi Capture system.
Provides structured logging with consistent formatting matching AI Processor.
"""

import sys
from typing import Optional, Dict, Any


class CaptureLogger:
    """
    Custom logger for Pi Capture operations with consistent formatting.
    Matches the AI Processor's bracketed format for unified logging.
    """
    
    # Log level prefixes matching AI Processor format
    PREFIXES = {
        'setup': '[SETUP]',
        'ok': '[OK]',
        'error': '[ERROR]',
        'warning': '[WARNING]',
        'info': '[INFO]',
        'debug': '[DEBUG]',
        'database': '[DATABASE]',
        'camera': '[CAMERA]',
        'motion': '[MOTION]',
        'video': '[VIDEO]',
        'sync': '[SYNC]',
        'scheduler': '[SCHEDULER]',
        'cleanup': '[CLEANUP]',
        'network': '[NETWORK]',
        'config': '[CONFIG]',
        'web': '[WEB]',
        'storage': '[STORAGE]',
        'stop': '[STOP]',
        'capture': '[CAPTURE]',
        'trigger': '[TRIGGER]',
        'link': '[LINK]',
    }
    
    def __init__(self, service_name: str = "pi-capture"):
        self.service_name = service_name
    
    def _format_message(self, level: str, message: str, extra: Optional[Dict[str, Any]] = None) -> str:
        """Format a log message with consistent structure."""
        prefix = self.PREFIXES.get(level.lower(), f'[{level.upper()}]')
        
        # Build the base message
        formatted = f"{prefix} {message}"
        
        # Add structured extra data if provided
        if extra:
            extra_str = " | ".join([f"{k}={v}" for k, v in extra.items()])
            formatted += f" | {extra_str}"
        
        return formatted
    
    def setup(self, message: str, **kwargs):
        """Log setup operations."""
        print(self._format_message('setup', message, kwargs))
    
    def ok(self, message: str, **kwargs):
        """Log successful operations."""
        print(self._format_message('ok', message, kwargs))
    
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Log errors with optional exception details."""
        if exception:
            kwargs['error'] = str(exception)
            kwargs['error_type'] = type(exception).__name__
        print(self._format_message('error', message, kwargs), file=sys.stderr)
    
    def warning(self, message: str, **kwargs):
        """Log warnings."""
        print(self._format_message('warning', message, kwargs))
    
    def info(self, message: str, **kwargs):
        """Log general information."""
        print(self._format_message('info', message, kwargs))
    
    def debug(self, message: str, **kwargs):
        """Log debug information."""
        print(self._format_message('debug', message, kwargs))
    
    def database(self, message: str, **kwargs):
        """Log database operations."""
        print(self._format_message('database', message, kwargs))
    
    def camera(self, message: str, **kwargs):
        """Log camera-related operations."""
        print(self._format_message('camera', message, kwargs))
    
    def motion(self, message: str, **kwargs):
        """Log motion detection operations."""
        print(self._format_message('motion', message, kwargs))
    
    def video(self, message: str, **kwargs):
        """Log video operations."""
        print(self._format_message('video', message, kwargs))
    
    def sync(self, message: str, **kwargs):
        """Log sync operations."""
        print(self._format_message('sync', message, kwargs))
    
    def scheduler(self, message: str, **kwargs):
        """Log scheduler operations."""
        print(self._format_message('scheduler', message, kwargs))
    
    def cleanup(self, message: str, **kwargs):
        """Log cleanup operations."""
        print(self._format_message('cleanup', message, kwargs))
    
    def capture(self, message: str, **kwargs):
        """Log capture operations."""
        print(self._format_message('capture', message, kwargs))
    
    def trigger(self, message: str, **kwargs):
        """Log trigger operations."""
        print(self._format_message('trigger', message, kwargs))
    
    def link(self, message: str, **kwargs):
        """Log camera linking operations."""
        print(self._format_message('link', message, kwargs))
    
    def web(self, message: str, **kwargs):
        """Log web interface operations."""
        print(self._format_message('web', message, kwargs))
    
    def config(self, message: str, **kwargs):
        """Log configuration operations."""
        print(self._format_message('config', message, kwargs))
    
    def network(self, message: str, **kwargs):
        """Log network operations."""
        print(self._format_message('network', message, kwargs))
    
    def storage(self, message: str, **kwargs):
        """Log storage operations."""
        print(self._format_message('storage', message, kwargs))
    
    def stop(self, message: str, **kwargs):
        """Log stop/shutdown operations."""
        print(self._format_message('stop', message, kwargs))


# Create a default logger instance
logger = CaptureLogger()