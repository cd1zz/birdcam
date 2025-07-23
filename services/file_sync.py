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

# Alternative: Context manager approach for even cleaner code
class ResilientAPIClient:
    """Context manager for resilient API calls"""
    
    def __init__(self, base_url: str, timeout: int = 10, max_retries: int = 3):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
    
    @retry_on_network_error(max_retries=3, delay=1.5, backoff=1.5)
    def get(self, endpoint: str, **kwargs) -> requests.Response:
        """GET request with retries"""
        return self.session.get(f"{self.base_url}{endpoint}", timeout=self.timeout, **kwargs)
    
    @retry_on_network_error(max_retries=3, delay=1.5, backoff=1.5)
    def post(self, endpoint: str, **kwargs) -> requests.Response:
        """POST request with retries"""
        return self.session.post(f"{self.base_url}{endpoint}", timeout=self.timeout, **kwargs)

# Example of using the context manager approach:
# with ResilientAPIClient("http://192.168.1.136:8091") as client:
#     response = client.get("/api/status")
#     data = response.json()

# Advanced: Circuit breaker pattern for even more resilience
class CircuitBreaker:
    """Simple circuit breaker to avoid overwhelming failing services"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func: Callable, *args, **kwargs):
        """Execute function through circuit breaker"""
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.timeout:
                self.state = 'HALF_OPEN'
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise e
    
    def on_success(self):
        """Reset circuit breaker on successful call"""
        self.failure_count = 0
        self.state = 'CLOSED'
    
    def on_failure(self):
        """Handle failure - may open circuit"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
            logger.warning(f"Circuit breaker OPENED after {self.failure_count} failures")
