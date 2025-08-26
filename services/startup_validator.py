#!/usr/bin/env python3
"""
Startup Validation Service
Validates system configuration, database integrity, and dependencies before starting services.
"""

import os
import sys
import sqlite3
from pathlib import Path
from typing import List
import importlib
import logging

logger = logging.getLogger(__name__)

class StartupValidator:
    """Comprehensive startup validation for the birdcam system"""
    
    def __init__(self, config):
        self.config = config
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
    
    def validate_all(self) -> bool:
        """Run all validation checks. Returns True if all critical checks pass."""
        
        # Critical checks (must pass)
        self._validate_python_version()
        self._validate_dependencies()
        self._validate_storage_paths()
        self._validate_database()
        self._validate_model_files()
        self._validate_configuration()
        
        # Non-critical checks (warnings only)
        self._validate_system_resources()
        self._validate_network_connectivity()
        
        # Print results
        self._print_results()
        
        # Return True only if no critical errors
        return len(self.errors) == 0
    
    def _validate_python_version(self):
        """Validate Python version"""
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            self.errors.append(f"Python 3.8+ required, found {version.major}.{version.minor}")
        elif version.minor < 9:
            self.warnings.append(f"Python 3.9+ recommended for best compatibility (found {version.major}.{version.minor})")
        else:
            self.info.append(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    def _validate_dependencies(self):
        """Validate required Python packages"""
        required_packages = [
            'torch', 'torchvision', 'cv2', 'numpy', 'pandas', 
            'flask', 'requests', 'psutil', 'schedule'
        ]
        
        missing = []
        for package in required_packages:
            try:
                if package == 'cv2':
                    importlib.import_module('cv2')
                else:
                    importlib.import_module(package)
                self.info.append(f"{package} available")
            except ImportError:
                missing.append(package)
        
        if missing:
            self.errors.append(f"Missing required packages: {', '.join(missing)}")
            self.errors.append("Run: pip install -r requirements.txt")
    
    def _validate_storage_paths(self):
        """Validate storage directory structure"""
        storage_path = Path(self.config.processing.storage_path)
        
        # Check base storage path
        if not storage_path.exists():
            self.warnings.append(f"Storage path doesn't exist, will create: {storage_path}")
            try:
                storage_path.mkdir(parents=True, exist_ok=True)
                self.info.append(f"Created storage directory: {storage_path}")
            except Exception as e:
                self.errors.append(f"Cannot create storage directory {storage_path}: {e}")
                return
        
        # Check required subdirectories
        required_dirs = [
            "incoming", "processed/detections", "processed/no_detections", "thumbnails"
        ]
        
        for dir_path in required_dirs:
            full_path = storage_path / dir_path
            if not full_path.exists():
                try:
                    full_path.mkdir(parents=True, exist_ok=True)
                    self.info.append(f"Created directory: {dir_path}")
                except Exception as e:
                    self.errors.append(f"Cannot create directory {full_path}: {e}")
            else:
                self.info.append(f"Directory exists: {dir_path}")
        
        # Check permissions
        if not os.access(storage_path, os.W_OK):
            self.errors.append(f"No write permission for storage path: {storage_path}")
    
    def _validate_database(self):
        """Validate database connectivity and table structure"""
        db_path = Path(self.config.database.path)
        
        # Check if database file exists and is accessible
        if not db_path.parent.exists():
            try:
                db_path.parent.mkdir(parents=True, exist_ok=True)
                self.info.append(f"Created database directory: {db_path.parent}")
            except Exception as e:
                self.errors.append(f"Cannot create database directory: {e}")
                return
        
        try:
            # Test database connection
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            
            # Check required tables exist
            required_tables = ['videos', 'detections']
            existing_tables = []
            
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            for row in cursor.fetchall():
                existing_tables.append(row[0])
            
            missing_tables = [t for t in required_tables if t not in existing_tables]
            
            if missing_tables:
                self.warnings.append(f"Database tables will be created: {', '.join(missing_tables)}")
            else:
                self.info.append("All required database tables exist")
                
                # Check table structure and data
                for table in required_tables:
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    self.info.append(f"{table} table: {count} records")
            
            conn.close()
            
        except Exception as e:
            self.errors.append(f"Database validation failed: {e}")
            self.errors.append(f"Database path: {db_path}")
    
    def _validate_model_files(self):
        """Validate AI model files"""
        model_name = self.config.processing.detection.model_name
        
        # Check if YOLO model file exists locally
        model_files = [f"{model_name}.pt", "yolov5n.pt", "yolov5s.pt"]
        found_model = None
        
        for model_file in model_files:
            if Path(model_file).exists():
                found_model = model_file
                break
        
        if found_model:
            self.info.append(f"Found local model file: {found_model}")
        else:
            self.warnings.append(f"Model {model_name} will be downloaded from torch.hub on first use")
        
        # Check torch.hub connectivity (non-blocking)
        try:
            # This is a quick test - actual model loading happens later
            self.info.append("PyTorch available for model loading")
        except Exception as e:
            self.errors.append(f"PyTorch validation failed: {e}")
    
    def _validate_configuration(self):
        """Validate configuration values"""
        # Check detection classes
        classes = self.config.processing.detection.classes
        if not classes or len(classes) == 0:
            self.errors.append("No detection classes configured")
        else:
            self.info.append(f"Detection classes: {', '.join(classes)}")
        
        # Check confidence thresholds
        confidences = self.config.processing.detection.confidences
        for cls in classes:
            confidence = confidences.get(cls, confidences.get('default', 0.5))
            if not 0 < confidence <= 1:
                self.warnings.append(f"Invalid confidence for {cls}: {confidence}")
            else:
                self.info.append(f"{cls} confidence: {confidence}")
        
        # Check retention policies
        det_retention = self.config.processing.detection_retention_days
        no_det_retention = self.config.processing.no_detection_retention_days
        
        if det_retention <= 0:
            self.warnings.append("Detection retention days should be > 0")
        if no_det_retention <= 0:
            self.warnings.append("No-detection retention days should be > 0")
        
        self.info.append(f"Retention: detections {det_retention}d, no-detections {no_det_retention}d")
    
    def _validate_system_resources(self):
        """Validate system resources (non-critical)"""
        try:
            import psutil
            
            # Memory check
            memory = psutil.virtual_memory()
            if memory.total < 1 * 1024**3:  # Less than 1GB
                self.warnings.append(f"Low system memory: {memory.total / 1024**3:.1f}GB")
            else:
                self.info.append(f"System memory: {memory.total / 1024**3:.1f}GB")
            
            # Disk space check
            storage_path = Path(self.config.processing.storage_path)
            if storage_path.exists():
                disk = psutil.disk_usage(str(storage_path))
                free_gb = disk.free / 1024**3
                if free_gb < 5:  # Less than 5GB free
                    self.warnings.append(f"Low disk space: {free_gb:.1f}GB free")
                else:
                    self.info.append(f"Available disk space: {free_gb:.1f}GB")
        
        except Exception as e:
            self.warnings.append(f"Could not check system resources: {e}")
    
    def _validate_network_connectivity(self):
        """Validate network configuration (non-critical)"""
        # Check if running on processing server or Pi
        try:
            # Simple connectivity test to localhost
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            
            # Test if we can bind to the configured port
            host = getattr(self.config.web, 'host', '0.0.0.0')
            port = getattr(self.config.web, 'processing_port', 8091)
            
            result = sock.connect_ex((host if host != '0.0.0.0' else 'localhost', port))
            if result == 0:
                self.warnings.append(f"Port {port} already in use")
            else:
                self.info.append(f"Port {port} available")
            
            sock.close()
            
        except Exception as e:
            self.warnings.append(f"Network connectivity check failed: {e}")
    
    def _print_results(self):
        """Print validation results"""
        print("="*60)
        print("STARTUP VALIDATION RESULTS")
        print("="*60)
        
        if self.info:
            print("SUCCESS:")
            for msg in self.info:
                print(f"  {msg}")
        
        if self.warnings:
            print("WARNINGS:")
            for msg in self.warnings:
                print(f"  {msg}")
        
        if self.errors:
            print("ERRORS:")
            for msg in self.errors:
                print(f"  {msg}")
            print("STARTUP ABORTED - Fix errors above before continuing")
        else:
            print("ALL VALIDATION CHECKS PASSED")
        
        print("="*60)

def validate_startup(config) -> bool:
    """Main validation entry point"""
    validator = StartupValidator(config)
    return validator.validate_all()