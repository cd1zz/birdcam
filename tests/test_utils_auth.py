"""Tests for authentication utility functions."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
import jwt
from utils.auth import (
    jwt_manager,
    hash_password,
    verify_password
)


class TestAuthUtils:
    """Test cases for authentication utilities."""
    
    @pytest.fixture
    def secret_key(self):
        """Test secret key."""
        return "test_secret_key_for_testing"
    
    def test_create_access_token_basic(self, secret_key):
        """Test basic access token generation."""
        with patch.object(jwt_manager, 'secret_key', secret_key):
            token = jwt_manager.create_access_token({"user_id": 123})
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode and verify
        decoded = jwt.decode(token, secret_key, algorithms=["HS256"])
        assert decoded["user_id"] == 123
        assert decoded["type"] == "access"
        assert "exp" in decoded
    
    def test_create_refresh_token(self, secret_key):
        """Test refresh token generation."""
        with patch.object(jwt_manager, 'secret_key', secret_key):
            token = jwt_manager.create_refresh_token({"user_id": 456})
        
        decoded = jwt.decode(token, secret_key, algorithms=["HS256"])
        assert decoded["user_id"] == 456
        assert decoded["type"] == "refresh"
        assert "exp" in decoded
    
    def test_create_token_with_additional_claims(self, secret_key):
        """Test token with multiple claims."""
        claims = {
            "user_id": 789,
            "role": "admin",
            "purpose": "api_access"
        }
        
        with patch.object(jwt_manager, 'secret_key', secret_key):
            token = jwt_manager.create_access_token(claims)
        
        decoded = jwt.decode(token, secret_key, algorithms=["HS256"])
        assert decoded["user_id"] == 789
        assert decoded["role"] == "admin"
        assert decoded["purpose"] == "api_access"
    
    def test_decode_token_valid(self, secret_key):
        """Test decoding of valid token."""
        with patch.object(jwt_manager, 'secret_key', secret_key):
            token = jwt_manager.create_access_token({"user_id": 999})
            payload = jwt_manager.decode_token(token)
        
        assert payload is not None
        assert payload["user_id"] == 999
    
    def test_decode_token_expired(self, secret_key):
        """Test decoding of expired token."""
        # Create expired token manually
        from datetime import timezone
        expired_time = datetime.now(timezone.utc) - timedelta(hours=1)
        token_data = {"user_id": 111, "exp": expired_time}
        token = jwt.encode(token_data, secret_key, algorithm="HS256")
        
        with patch.object(jwt_manager, 'secret_key', secret_key):
            payload = jwt_manager.decode_token(token)
        
        assert payload is None
    
    def test_decode_token_invalid_signature(self, secret_key):
        """Test decoding with wrong secret key."""
        with patch.object(jwt_manager, 'secret_key', secret_key):
            token = jwt_manager.create_access_token({"user_id": 222})
        
        # Try to decode with different secret
        with patch.object(jwt_manager, 'secret_key', 'wrong_secret'):
            payload = jwt_manager.decode_token(token)
        
        assert payload is None
    
    def test_decode_token_malformed(self):
        """Test decoding of malformed token."""
        payload = jwt_manager.decode_token("not.a.valid.token")
        assert payload is None
        
        payload = jwt_manager.decode_token("invalid")
        assert payload is None
        
        payload = jwt_manager.decode_token("")
        assert payload is None
    
    def test_hash_password(self):
        """Test password hashing."""
        password = "MySecurePassword123!"
        hashed = hash_password(password)
        
        assert isinstance(hashed, str)
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt prefix
        assert len(hashed) == 60  # bcrypt hash length
    
    def test_hash_password_different_hashes(self):
        """Test that same password produces different hashes."""
        password = "TestPassword456"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        assert hash1 != hash2  # Different salts
    
    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "CorrectPassword789"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test password verification with wrong password."""
        password = "CorrectPassword789"
        hashed = hash_password(password)
        
        assert verify_password("WrongPassword", hashed) is False
        assert verify_password("correctpassword789", hashed) is False  # Case sensitive
        assert verify_password("CorrectPassword78", hashed) is False  # Missing char
    
    def test_verify_password_invalid_hash(self):
        """Test password verification with invalid hash."""
        # bcrypt raises ValueError for invalid hashes
        try:
            result = verify_password("password", "not_a_hash")
            # If no exception, it should return False
            assert result is False
        except ValueError:
            # This is expected for invalid bcrypt format
            pass
        
        try:
            result = verify_password("password", "")
            assert result is False
        except ValueError:
            pass
            
        try:
            result = verify_password("password", "$2b$invalid")
            assert result is False
        except ValueError:
            pass
    
    def test_verify_token_type(self, secret_key):
        """Test token type verification."""
        with patch.object(jwt_manager, 'secret_key', secret_key):
            access_token = jwt_manager.create_access_token({"user_id": 555})
            refresh_token = jwt_manager.create_refresh_token({"user_id": 666})
            
            # Verify access token
            access_payload = jwt_manager.verify_token(access_token, token_type="access")
            assert access_payload is not None
            assert access_payload["user_id"] == 555
            assert access_payload["type"] == "access"
            
            # Verify refresh token
            refresh_payload = jwt_manager.verify_token(refresh_token, token_type="refresh")
            assert refresh_payload is not None
            assert refresh_payload["user_id"] == 666
            assert refresh_payload["type"] == "refresh"
            
            # Wrong type should fail
            wrong_type = jwt_manager.verify_token(access_token, token_type="refresh")
            assert wrong_type is None
    
    def test_password_edge_cases(self):
        """Test password functions with edge cases."""
        # Empty password
        empty_hash = hash_password("")
        assert verify_password("", empty_hash) is True
        assert verify_password("not_empty", empty_hash) is False
        
        # Very long password
        long_password = "x" * 1000
        long_hash = hash_password(long_password)
        assert verify_password(long_password, long_hash) is True
        
        # Special characters
        special_password = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        special_hash = hash_password(special_password)
        assert verify_password(special_password, special_hash) is True
    
    def test_token_algorithms(self, secret_key):
        """Test that only HS256 algorithm is accepted."""
        # Create token with different algorithm
        token_hs512 = jwt.encode(
            {"user_id": 888, "type": "access"},
            secret_key,
            algorithm="HS512"  # Different algorithm
        )
        
        with patch.object(jwt_manager, 'secret_key', secret_key):
            # Should fail because jwt_manager only accepts HS256
            payload = jwt_manager.decode_token(token_hs512)
            
        # Should return None as algorithm doesn't match
        assert payload is None