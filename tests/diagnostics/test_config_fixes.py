#!/usr/bin/env python3
"""
Test suite for configuration system fixes
"""
import pytest
import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.settings import get_list_env


class TestConfigurationFixes:
    """Test configuration system fixes"""
    
    def test_get_list_env_mutable_default_fix(self):
        """Test that get_list_env doesn't share mutable defaults"""
        # Test with default value
        result1 = get_list_env('NONEXISTENT_VAR', ['default1'])
        result2 = get_list_env('NONEXISTENT_VAR', ['default2'])
        
        # Modify one result
        result1.append('modified')
        
        # Verify that result2 is not affected
        assert result2 == ['default2']
        assert 'modified' not in result2
        
        # Test with None default
        result3 = get_list_env('NONEXISTENT_VAR2')
        result4 = get_list_env('NONEXISTENT_VAR2')
        
        # Modify one result
        result3.append('test')
        
        # Verify that result4 is not affected
        assert result4 == []
        assert 'test' not in result4
    
    def test_get_list_env_returns_copy(self):
        """Test that get_list_env returns a copy of the default"""
        default = ['item1', 'item2']
        result = get_list_env('NONEXISTENT_VAR', default)
        
        # Modify the result
        result.append('item3')
        
        # Verify that original default is unchanged
        assert default == ['item1', 'item2']
        assert 'item3' not in default
    
    def test_get_list_env_normal_functionality(self):
        """Test that get_list_env still works normally"""
        # Test with environment variable set
        os.environ['TEST_LIST_VAR'] = 'item1,item2,item3'
        
        result = get_list_env('TEST_LIST_VAR')
        assert result == ['item1', 'item2', 'item3']
        
        # Test with whitespace
        os.environ['TEST_LIST_VAR_SPACE'] = ' item1 , item2 , item3 '
        result = get_list_env('TEST_LIST_VAR_SPACE')
        assert result == ['item1', 'item2', 'item3']
        
        # Test with empty string
        os.environ['TEST_LIST_VAR_EMPTY'] = ''
        result = get_list_env('TEST_LIST_VAR_EMPTY', ['default'])
        assert result == ['default']
        
        # Cleanup
        del os.environ['TEST_LIST_VAR']
        del os.environ['TEST_LIST_VAR_SPACE']
        del os.environ['TEST_LIST_VAR_EMPTY']
    
    def test_get_list_env_empty_items_filtered(self):
        """Test that empty items are filtered out"""
        os.environ['TEST_LIST_EMPTY_ITEMS'] = 'item1,,item2, ,item3'
        
        result = get_list_env('TEST_LIST_EMPTY_ITEMS')
        assert result == ['item1', 'item2', 'item3']
        
        # Cleanup
        del os.environ['TEST_LIST_EMPTY_ITEMS']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])