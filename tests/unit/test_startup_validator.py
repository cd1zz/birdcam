#!/usr/bin/env python3
"""
Unit tests for startup validator
"""

import pytest
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import Mock, patch
import sys

from services.startup_validator import StartupValidator


class TestStartupValidator:
    """Test startup validation functionality"""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration"""
        config = Mock()
        
        # Database config
        config.database.path = ":memory:"
        
        # Processing config
        config.processing.storage_path = Path("/tmp/test_storage")
        config.processing.detection.classes = ['bird', 'cat', 'dog']
        config.processing.detection.confidences = {'bird': 0.5, 'cat': 0.6, 'default': 0.5}
        config.processing.detection.model_name = 'yolov5n'
        config.processing.detection_retention_days = 30
        config.processing.no_detection_retention_days = 7
        
        # Web config
        config.web.host = '0.0.0.0'
        config.web.processing_port = 8091
        
        return config
    
    def test_python_version_validation(self, mock_config):
        """Test Python version validation"""
        validator = StartupValidator(mock_config)
        
        # Test current version (should pass)
        validator._validate_python_version()
        
        # Should have at least one info message about Python version
        python_messages = [msg for msg in validator.info if 'Python version' in msg]
        assert len(python_messages) > 0
    
    def test_dependency_validation(self, mock_config):
        """Test dependency validation"""
        validator = StartupValidator(mock_config)
        
        # This will test real dependencies on the system
        validator._validate_dependencies()
        
        # Should either have success messages or error messages, not both for same package
        torch_success = any('torch' in msg for msg in validator.info)
        torch_error = any('torch' in msg for msg in validator.errors)
        
        # Exactly one should be true (either torch is available or it's missing)
        assert torch_success != torch_error  # XOR
    
    def test_storage_path_validation(self, mock_config):
        """Test storage path validation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.processing.storage_path = Path(temp_dir)
            validator = StartupValidator(mock_config)
            
            validator._validate_storage_paths()
            
            # Should have created required directories
            required_dirs = [
                "incoming", "processed/detections", "processed/no_detections", "thumbnails"
            ]
            
            for dir_name in required_dirs:
                dir_path = Path(temp_dir) / dir_name
                assert dir_path.exists(), f"Directory not created: {dir_name}"
            
            # Should have success messages
            success_messages = [msg for msg in validator.info if 'Created directory' in msg or 'Directory exists' in msg]
            assert len(success_messages) > 0
    
    def test_database_validation_success(self, mock_config):
        """Test successful database validation"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            mock_config.database.path = Path(db_path)
            
            # Create database with proper tables
            conn = sqlite3.connect(db_path)
            conn.execute('''CREATE TABLE videos (id INTEGER PRIMARY KEY)''')
            conn.execute('''CREATE TABLE detections (id INTEGER PRIMARY KEY)''')
            conn.close()
            
            validator = StartupValidator(mock_config)
            validator._validate_database()
            
            # Should have success message about tables existing
            table_messages = [msg for msg in validator.info if 'database tables exist' in msg]
            assert len(table_messages) > 0
            
        finally:
            Path(db_path).unlink(missing_ok=True)
    
    def test_database_validation_missing_tables(self, mock_config):
        """Test database validation with missing tables"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            mock_config.database.path = Path(db_path)
            
            # Create empty database (no tables)
            conn = sqlite3.connect(db_path)
            conn.close()
            
            validator = StartupValidator(mock_config)
            validator._validate_database()
            
            # Should have warning about creating tables
            warning_messages = [msg for msg in validator.warnings if 'tables will be created' in msg]
            assert len(warning_messages) > 0
            
        finally:
            Path(db_path).unlink(missing_ok=True)
    
    def test_database_validation_failure(self, mock_config):
        """Test database validation failure scenarios"""
        # Test with invalid database path
        mock_config.database.path = Path("/invalid/path/database.db")
        
        validator = StartupValidator(mock_config)
        validator._validate_database()
        
        # Should have error message
        assert len(validator.errors) > 0
        # Check for database related error messages
        db_error_messages = [msg for msg in validator.errors if 'database' in msg.lower() or 'Database directory' in msg]
        assert len(db_error_messages) > 0
    
    def test_configuration_validation(self, mock_config):
        """Test configuration validation"""
        validator = StartupValidator(mock_config)
        validator._validate_configuration()
        
        # Should validate detection classes
        class_messages = [msg for msg in validator.info if 'Detection classes:' in msg]
        assert len(class_messages) > 0
        
        # Should validate confidence thresholds
        confidence_messages = [msg for msg in validator.info if 'confidence:' in msg]
        assert len(confidence_messages) > 0
        
        # Should validate retention policies
        retention_messages = [msg for msg in validator.info if 'Retention:' in msg]
        assert len(retention_messages) > 0
    
    def test_configuration_validation_errors(self, mock_config):
        """Test configuration validation with errors"""
        # Test with empty detection classes
        mock_config.processing.detection.classes = []
        
        validator = StartupValidator(mock_config)
        validator._validate_configuration()
        
        # Should have error about no detection classes
        error_messages = [msg for msg in validator.errors if 'No detection classes' in msg]
        assert len(error_messages) > 0
    
    def test_model_validation(self, mock_config):
        """Test AI model validation"""
        validator = StartupValidator(mock_config)
        validator._validate_model_files()
        
        # Should have either found a local model or note that it will be downloaded
        model_messages = validator.info + validator.warnings
        model_refs = [msg for msg in model_messages if 'model' in msg.lower()]
        assert len(model_refs) > 0
    
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_system_resources_validation(self, mock_disk, mock_memory, mock_config):
        """Test system resources validation"""
        # Mock sufficient resources
        mock_memory.return_value.total = 4 * 1024**3  # 4GB
        mock_disk.return_value.free = 10 * 1024**3   # 10GB
        
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.processing.storage_path = Path(temp_dir)
            
            validator = StartupValidator(mock_config)
            validator._validate_system_resources()
            
            # Should have success messages
            memory_messages = [msg for msg in validator.info if 'System memory:' in msg]
            disk_messages = [msg for msg in validator.info if 'Available disk space:' in msg]
            
            assert len(memory_messages) > 0
            assert len(disk_messages) > 0
    
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_system_resources_warnings(self, mock_disk, mock_memory, mock_config):
        """Test system resources validation with low resources"""
        # Mock insufficient resources
        mock_memory.return_value.total = 512 * 1024**2  # 512MB
        mock_disk.return_value.free = 1 * 1024**3       # 1GB
        
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.processing.storage_path = Path(temp_dir)
            
            validator = StartupValidator(mock_config)
            validator._validate_system_resources()
            
            # Should have warning messages
            memory_warnings = [msg for msg in validator.warnings if 'Low system memory' in msg]
            disk_warnings = [msg for msg in validator.warnings if 'Low disk space' in msg]
            
            assert len(memory_warnings) > 0
            assert len(disk_warnings) > 0
    
    def test_validate_all_success(self, mock_config):
        """Test complete validation with successful outcome"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.processing.storage_path = Path(temp_dir)
            
            # Create a valid database
            db_path = Path(temp_dir) / "test.db"
            mock_config.database.path = db_path
            
            conn = sqlite3.connect(str(db_path))
            conn.execute('''CREATE TABLE videos (id INTEGER PRIMARY KEY)''')
            conn.execute('''CREATE TABLE detections (id INTEGER PRIMARY KEY)''')
            conn.close()
            
            validator = StartupValidator(mock_config)
            
            # Mock successful dependency check
            with patch.object(validator, '_validate_dependencies'):
                result = validator.validate_all()
            
            # Should pass validation
            assert result is True
            assert len(validator.errors) == 0
    
    def test_validate_all_failure(self, mock_config):
        """Test complete validation with failures"""
        # Set invalid configuration
        mock_config.processing.detection.classes = []  # No classes
        mock_config.database.path = Path("/invalid/path/db.db")  # Invalid path
        
        validator = StartupValidator(mock_config)
        result = validator.validate_all()
        
        # Should fail validation
        assert result is False
        assert len(validator.errors) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])