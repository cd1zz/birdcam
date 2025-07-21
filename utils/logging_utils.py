"""
Logging utilities for consistent logging across the birdcam system.
Provides structured logging with consistent formatting and log levels.
"""

import sys
from datetime import datetime
from typing import Optional, Dict, Any
import json


class ProcessingLogger:
    """
    Custom logger for AI processing operations with consistent formatting.
    Uses print statements that are captured by systemd journal.
    """
    
    # Log level prefixes with consistent formatting
    PREFIXES = {
        'stats': '[STATS]',
        'ok': '[OK]',
        'error': '[ERROR]',
        'warning': '[WARNING]',
        'info': '[INFO]',
        'debug': '[DEBUG]',
        'processing': '[PROCESSING]',
        'detection': '[DETECTION]',
        'video': '[VIDEO]',
        'storage': '[STORAGE]',
        'cleanup': '[CLEANUP]',
        'ai': '[AI]',
        'received': '[RECEIVED]',
        'config': '[CONFIG]',
        'scheduler': '[SCHEDULER]',
        'network': '[NETWORK]',
        'search': '[SEARCH]',
        'thumbnails': '[THUMBNAILS]',
        'pause': '[PAUSE]',
        'empty': '[EMPTY]',
        'stop': '[STOP]',
        'validation': '[VALIDATION]',
        'web': '[WEB]',
        'log': '[LOG]',
        'gpu': '[GPU]',
        'cpu': '[CPU]',
    }
    
    def __init__(self, service_name: str = "ai-processor"):
        self.service_name = service_name
    
    def _format_message(self, level: str, message: str, extra: Optional[Dict[str, Any]] = None) -> str:
        """Format a log message with consistent structure."""
        prefix = self.PREFIXES.get(level.lower(), f'[{level.upper()}]')
        
        # Build the base message
        formatted = f"{prefix} {message}"
        
        # Add structured extra data if provided
        if extra:
            # For progress logs, format differently
            if level == 'stats' and 'progress' in extra:
                formatted = f"{prefix} Progress: {extra['progress']:.1f}%"
                if 'video' in extra:
                    formatted += f" - {extra['video']}"
            else:
                # For other logs, append key-value pairs
                extra_str = " | ".join([f"{k}={v}" for k, v in extra.items()])
                formatted += f" | {extra_str}"
        
        return formatted
    
    def stats(self, message: str, **kwargs):
        """Log statistics and progress information."""
        print(self._format_message('stats', message, kwargs))
    
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
    
    def processing(self, message: str, **kwargs):
        """Log processing operations."""
        print(self._format_message('processing', message, kwargs))
    
    def detection(self, message: str, **kwargs):
        """Log detection-related information."""
        print(self._format_message('detection', message, kwargs))
    
    def storage(self, message: str, **kwargs):
        """Log storage operations."""
        print(self._format_message('storage', message, kwargs))
    
    def cleanup(self, message: str, **kwargs):
        """Log cleanup operations."""
        print(self._format_message('cleanup', message, kwargs))
    
    def ai(self, message: str, **kwargs):
        """Log AI model operations."""
        print(self._format_message('ai', message, kwargs))
    
    def progress(self, current: int, total: int, video_name: Optional[str] = None):
        """Log progress with consistent formatting."""
        progress = (current / total) * 100 if total > 0 else 0
        extra = {'progress': progress}
        if video_name:
            extra['video'] = video_name
        self.stats("Processing video", **extra)
    
    def processing_complete(self, video_name: str, detections: int, processing_time: float, 
                          classes: Optional[list] = None, destination: Optional[str] = None):
        """Log completion of video processing with all relevant details."""
        extra = {
            'video': video_name,
            'detections': detections,
            'time': f"{processing_time:.1f}s"
        }
        
        if classes:
            extra['classes'] = ', '.join(classes)
        
        if destination:
            extra['destination'] = destination
        
        if detections > 0:
            self.detection(f"Processed {video_name}", **extra)
        else:
            self.video(f"Processed {video_name} (no detections)", **extra)
    
    def video(self, message: str, **kwargs):
        """Log video-related operations."""
        print(self._format_message('video', message, kwargs))
    
    def batch_summary(self, processed: int, total: int, duration: float):
        """Log batch processing summary."""
        success_rate = (processed / total * 100) if total > 0 else 0
        self.ok(f"Batch complete", processed=processed, total=total, 
                success_rate=f"{success_rate:.1f}%", duration=f"{duration:.1f}s")


# Create a default logger instance
logger = ProcessingLogger()