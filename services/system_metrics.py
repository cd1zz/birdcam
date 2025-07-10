"""
System metrics collection service for monitoring CPU, memory, and disk usage.
"""

import psutil
import time
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class SystemMetrics:
    """System metrics data model"""
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    disk_free_gb: float
    timestamp: float


class SystemMetricsCollector:
    """Collects system metrics using psutil"""
    
    def __init__(self, storage_path: str = "/"):
        self.storage_path = storage_path
    
    def get_metrics(self) -> SystemMetrics:
        """Get current system metrics"""
        # CPU usage (averaged over 1 second)
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_gb = memory.used / (1024**3)
        memory_total_gb = memory.total / (1024**3)
        
        # Disk usage for storage path
        disk = psutil.disk_usage(self.storage_path)
        disk_percent = (disk.used / disk.total) * 100
        disk_used_gb = disk.used / (1024**3)
        disk_total_gb = disk.total / (1024**3)
        disk_free_gb = disk.free / (1024**3)
        
        return SystemMetrics(
            cpu_percent=round(cpu_percent, 1),
            memory_percent=round(memory_percent, 1),
            memory_used_gb=round(memory_used_gb, 2),
            memory_total_gb=round(memory_total_gb, 2),
            disk_percent=round(disk_percent, 1),
            disk_used_gb=round(disk_used_gb, 2),
            disk_total_gb=round(disk_total_gb, 2),
            disk_free_gb=round(disk_free_gb, 2),
            timestamp=time.time()
        )
    
    def get_metrics_dict(self) -> Dict[str, Any]:
        """Get metrics as dictionary for JSON serialization"""
        metrics = self.get_metrics()
        return {
            'cpu_percent': metrics.cpu_percent,
            'memory_percent': metrics.memory_percent,
            'memory_used_gb': metrics.memory_used_gb,
            'memory_total_gb': metrics.memory_total_gb,
            'disk_percent': metrics.disk_percent,
            'disk_used_gb': metrics.disk_used_gb,
            'disk_total_gb': metrics.disk_total_gb,
            'disk_free_gb': metrics.disk_free_gb,
            'timestamp': metrics.timestamp
        }