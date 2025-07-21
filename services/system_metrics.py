"""
System metrics collection service for monitoring CPU, memory, and disk usage.
"""

import psutil
import time
import os
from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class DiskMetrics:
    """Disk usage metrics for a single drive"""
    device: str
    mountpoint: str
    fstype: str
    percent: float
    used_gb: float
    total_gb: float
    free_gb: float
    role: str = "other"  # Role: "boot", "storage", "other"


@dataclass
class SystemMetrics:
    """System metrics data model"""
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
    disks: List[DiskMetrics]
    timestamp: float


class SystemMetricsCollector:
    """Collects system metrics using psutil"""
    
    def __init__(self, storage_path: str = "/"):
        self.storage_path = storage_path
    
    def _get_storage_disks(self) -> List[DiskMetrics]:
        """Get disk metrics for all storage drives"""
        disks = []
        
        # Get all disk partitions
        partitions = psutil.disk_partitions()
        
        for partition in partitions:
            # Skip pseudo-filesystems and system partitions
            if partition.fstype in ('', 'tmpfs', 'devtmpfs', 'squashfs', 'proc', 'sysfs', 'devfs'):
                continue
            if partition.mountpoint in ('/dev', '/proc', '/sys', '/run', '/boot/efi'):
                continue
            if partition.mountpoint.startswith('/snap/'):
                continue
            
            try:
                # Get disk usage for this partition
                disk = psutil.disk_usage(partition.mountpoint)
                disk_percent = (disk.used / disk.total) * 100
                disk_used_gb = disk.used / (1024**3)
                disk_total_gb = disk.total / (1024**3)
                disk_free_gb = disk.free / (1024**3)
                
                disks.append(DiskMetrics(
                    device=partition.device,
                    mountpoint=partition.mountpoint,
                    fstype=partition.fstype,
                    percent=round(disk_percent, 1),
                    used_gb=round(disk_used_gb, 2),
                    total_gb=round(disk_total_gb, 2),
                    free_gb=round(disk_free_gb, 2)
                ))
            except PermissionError:
                # Skip drives we can't access
                continue
        
        return disks
    
    def get_metrics(self) -> SystemMetrics:
        """Get current system metrics"""
        # CPU usage (averaged over 1 second)
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_gb = memory.used / (1024**3)
        memory_total_gb = memory.total / (1024**3)
        
        # Get all disk metrics with role identification
        disks = []
        partitions = psutil.disk_partitions()
        
        # Identify which partition contains the storage path
        storage_mountpoint = None
        if self.storage_path and os.path.exists(self.storage_path):
            for partition in partitions:
                if self.storage_path.startswith(partition.mountpoint):
                    if not storage_mountpoint or len(partition.mountpoint) > len(storage_mountpoint):
                        storage_mountpoint = partition.mountpoint
        
        # Get metrics for all disks and assign roles
        for partition in partitions:
            # Skip system partitions
            if partition.fstype in ['tmpfs', 'squashfs', 'devtmpfs']:
                continue
            if partition.mountpoint.startswith('/snap/'):
                continue
            if partition.mountpoint == '/boot/efi':
                continue
            
            try:
                disk = psutil.disk_usage(partition.mountpoint)
                disk_percent = disk.percent
                disk_used_gb = disk.used / (1024**3)
                disk_total_gb = disk.total / (1024**3)
                disk_free_gb = disk.free / (1024**3)
                
                # Determine role
                role = "other"
                if partition.mountpoint == "/":
                    role = "boot"
                elif partition.mountpoint == storage_mountpoint:
                    role = "storage"
                
                disks.append(DiskMetrics(
                    device=partition.device,
                    mountpoint=partition.mountpoint,
                    fstype=partition.fstype,
                    percent=round(disk_percent, 1),
                    used_gb=round(disk_used_gb, 2),
                    total_gb=round(disk_total_gb, 2),
                    free_gb=round(disk_free_gb, 2),
                    role=role
                ))
            except PermissionError:
                # Skip drives we can't access
                continue
            except Exception as e:
                print(f"Error getting disk metrics for {partition.mountpoint}: {e}")
                continue
        
        # Sort disks by role priority: storage first, then boot, then others
        role_priority = {"storage": 0, "boot": 1, "other": 2}
        disks.sort(key=lambda d: (role_priority.get(d.role, 3), d.mountpoint))
        
        return SystemMetrics(
            cpu_percent=round(cpu_percent, 1),
            memory_percent=round(memory_percent, 1),
            memory_used_gb=round(memory_used_gb, 2),
            memory_total_gb=round(memory_total_gb, 2),
            disks=disks,
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
            'disks': [
                {
                    'device': disk.device,
                    'mountpoint': disk.mountpoint,
                    'fstype': disk.fstype,
                    'percent': disk.percent,
                    'used_gb': disk.used_gb,
                    'total_gb': disk.total_gb,
                    'free_gb': disk.free_gb,
                    'role': disk.role
                } for disk in metrics.disks
            ],
            'timestamp': metrics.timestamp
        }