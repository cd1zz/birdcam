# services/file_sync.py - Pythonic retry implementation

import requests
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
import time
import functools
from requests.exceptions import RequestException, Timeout, ConnectionError
from utils.capture_logger import logger

def retry_on_network_error(max_retries: int = 3, delay: float = 2.0, backoff: float = 1.0):
    """
    Decorator that retries a function on network errors.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay (exponential backoff if > 1.0)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):  # +1 for initial attempt
                try:
                    return func(*args, **kwargs)
                    
                except (RequestException, Timeout, ConnectionError) as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        logger.warning(f"{func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}), "
                                     f"retrying in {current_delay:.1f}s...")
                        time.sleep(current_delay)
                        current_delay *= backoff  # Exponential backoff
                    else:
                        logger.error(f"{func.__name__} failed after {max_retries + 1} attempts")
            
            # All retries exhausted
            raise last_exception
            
        return wrapper
    return decorator

class FileSyncService:
    def __init__(self, server_host: str, server_port: int = 8091, timeout: int = 10, secret_key: Optional[str] = None):
        self.server_host = server_host
        self.server_port = server_port
        self.timeout = timeout
        self.base_url = f"http://{server_host}:{server_port}"
        self.secret_key = secret_key
    
    @retry_on_network_error(max_retries=3, delay=2.0, backoff=1.5)
    def _get_request(self, endpoint: str, **kwargs) -> requests.Response:
        """Make GET request with automatic retries"""
        url = f"{self.base_url}{endpoint}"
        # Add secret key header if available
        if self.secret_key:
            headers = kwargs.get('headers', {})
            headers['X-Secret-Key'] = self.secret_key
            kwargs['headers'] = headers
        return requests.get(url, timeout=self.timeout, **kwargs)
    
    @retry_on_network_error(max_retries=3, delay=2.0, backoff=1.5)
    def _post_request(self, endpoint: str, **kwargs) -> requests.Response:
        """Make POST request with automatic retries"""
        url = f"{self.base_url}{endpoint}"
        # Add secret key header if available
        if self.secret_key:
            headers = kwargs.get('headers', {})
            headers['X-Secret-Key'] = self.secret_key
            kwargs['headers'] = headers
        return requests.post(url, timeout=self.timeout, **kwargs)
    
    def sync_file(self, file_path: Path, original_filename: str) -> bool:
        """Sync file to processing server"""
        if not file_path.exists():
            return False
        
        try:
            with open(file_path, 'rb') as f:
                files = {'video': (original_filename, f, 'video/mp4')}
                response = self._post_request('/upload', files=files)
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Failed to sync {original_filename}: {e}")
            return False
    
    def get_server_status(self) -> Dict[str, Any]:
        """Get status from processing server"""
        try:
            response = self._get_request('/api/status')
            if response.status_code == 200:
                status_data = response.json()
                status_data['connected'] = True
                return status_data
        except Exception as e:
            logger.warning(f"Could not reach processing server: {e}")
        
        return {'connected': False}
    
    def get_server_detections(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent detections from processing server"""
        try:
            response = self._get_request('/api/recent-detections')
            if response.status_code == 200:
                data = response.json()
                return data.get('detections', [])
        except Exception as e:
            logger.warning(f"Could not get detections: {e}")
        
        return []
    
    def trigger_processing(self) -> bool:
        """Trigger processing on server"""
        try:
            response = self._post_request('/api/process-now')
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Could not trigger processing: {e}")
            return False

    def delete_server_detection(self, detection_id: int) -> bool:
        """Request server to delete a detection"""
        try:
            response = self._post_request(
                '/api/delete-detection',
                json={'detection_id': detection_id},
                headers={'Content-Type': 'application/json'}
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Could not delete detection: {e}")
            return False
    
    def get_server_motion_settings(self) -> Optional[Dict[str, Any]]:
        """Get motion detection settings from server"""
        try:
            response = self._get_request('/api/motion-settings')
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.warning(f"Could not get motion settings: {e}")
        
        return None
    
    def update_server_motion_settings(self, settings: Dict[str, Any]) -> bool:
        """Update motion detection settings on server"""
        try:
            response = self._post_request(
                '/api/motion-settings',
                json=settings,
                headers={'Content-Type': 'application/json'}
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Could not update motion settings: {e}")
            return False
