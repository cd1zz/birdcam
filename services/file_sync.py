# services/file_sync.py
import requests
from pathlib import Path
from typing import List
import time
from requests.exceptions import RequestException, Timeout

class FileSyncService:
    def __init__(self, server_host: str, server_port: int = 8091, timeout: int = 300):
        self.server_host = server_host
        self.server_port = server_port
        self.timeout = timeout
        self.base_url = f"http://{server_host}:{server_port}"
    
    def sync_file(self, file_path: Path, original_filename: str) -> bool:
        if not file_path.exists():
            return False
        
        try:
            with open(file_path, 'rb') as f:
                files = {'video': (original_filename, f, 'video/mp4')}
                response = requests.post(
                    f"{self.base_url}/upload",
                    files=files,
                    timeout=self.timeout
                )
            
            return response.status_code == 200
            
        except (RequestException, Timeout):
            return False
    
    def get_server_status(self) -> dict:
        """Get status from processing server"""
        try:
            response = requests.get(f"{self.base_url}/api/status", timeout=5)
            if response.status_code == 200:
                status_data = response.json()
                # Add the 'connected' flag that the capture system expects
                status_data['connected'] = True
                return status_data
        except (RequestException, Timeout) as e:
            print(f"⚠️ Could not reach processing server: {e}")
        
        # Return disconnected status if request failed
        return {'connected': False}
    
    def trigger_processing(self) -> bool:
        try:
            response = requests.post(f"{self.base_url}/api/process-now", timeout=10)
            return response.status_code == 200
        except (RequestException, Timeout):
            return False
        
    def get_server_detections(self, limit: int = 10) -> List[dict]:
        """Get recent detections from processing server"""
        try:
            response = requests.get(
                f"{self.base_url}/api/recent-detections", 
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('detections', [])
        except (RequestException, Timeout) as e:
            print(f"⚠️ Could not get detections from processing server: {e}")
        
        return []