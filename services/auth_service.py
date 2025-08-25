# services/auth_service.py
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from core.models import User, UserRole
from database.repositories.user_repository import UserRepository
from utils.auth import hash_password, verify_password, jwt_manager
from utils.security_logger import log_auth_failed, log_auth_success, log_password_changed, log_role_changed, log_user_deactivated, log_token_refresh_failed
import logging

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
    
    def authenticate(self, username: str, password: str) -> Optional[Tuple[User, str, str]]:
        """
        Authenticate a user and return user object with tokens if successful.
        Returns: (User, access_token, refresh_token) or None
        """
        user = self.user_repository.get_by_username(username)
        
        if not user:
            log_auth_failed(username, "user_not_found")
            return None
            
        if not user.is_active:
            log_auth_failed(username, "account_disabled", {"user_id": user.id})
            return None
        
        if not verify_password(password, user.password_hash):
            log_auth_failed(username, "invalid_password", {"user_id": user.id})
            return None
        
        # Update last login
        self.user_repository.update_last_login(user.id)
        
        # Create tokens
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "role": user.role.value
        }
        access_token = jwt_manager.create_access_token(token_data)
        refresh_token = jwt_manager.create_refresh_token(token_data)
        
        # Log successful authentication
        log_auth_success(username, {"user_id": user.id, "role": user.role.value})
        
        return user, access_token, refresh_token
    
    def refresh_tokens(self, refresh_token: str) -> Optional[Tuple[str, str]]:
        """
        Refresh access token using refresh token.
        Returns: (new_access_token, new_refresh_token) or None
        """
        payload = jwt_manager.verify_token(refresh_token, token_type="refresh")
        if not payload:
            log_token_refresh_failed("invalid_token")
            return None
        
        user_id = int(payload.get("sub"))
        user = self.user_repository.get_by_id(user_id)
        
        if not user:
            log_token_refresh_failed("user_not_found", {"user_id": user_id})
            return None
            
        if not user.is_active:
            log_token_refresh_failed("account_disabled", {"user_id": user_id, "username": user.username})
            return None
        
        # Create new tokens
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "role": user.role.value
        }
        new_access_token = jwt_manager.create_access_token(token_data)
        new_refresh_token = jwt_manager.create_refresh_token(token_data)
        
        return new_access_token, new_refresh_token
    
    def create_user(self, username: str, password: str, role: UserRole = UserRole.VIEWER) -> Optional[User]:
        """Create a new user."""
        # Check if username already exists (case-insensitive)
        if self.user_repository.get_by_username(username):
            logger.warning(f"Attempted to create duplicate user: {username}")
            return None
        
        # Hash password
        password_hash = hash_password(password)
        
        # Create user with lowercase username
        user = User(
            id=None,
            username=username.lower(),
            password_hash=password_hash,
            role=role,
            is_active=True
        )
        
        user_id = self.user_repository.create(user)
        user.id = user_id
        
        logger.info(f"Created new user: {username.lower()} with role {role.value}")
        return user
    
    def update_password(self, user_id: int, new_password: str) -> bool:
        """Update user password."""
        user = self.user_repository.get_by_id(user_id)
        if not user:
            return False
        
        user.password_hash = hash_password(new_password)
        self.user_repository.update(user)
        
        logger.info(f"Updated password for user: {user.username}")
        log_password_changed(user.username)
        return True
    
    def update_role(self, user_id: int, new_role: UserRole, changed_by: str = None) -> bool:
        """Update user role."""
        user = self.user_repository.get_by_id(user_id)
        if not user:
            return False
        
        # Prevent removing last admin
        if user.role == UserRole.ADMIN and new_role != UserRole.ADMIN:
            admin_count = self.user_repository.count_by_role(UserRole.ADMIN)
            if admin_count <= 1:
                logger.warning("Cannot remove last admin user")
                return False
        
        old_role = user.role
        user.role = new_role
        self.user_repository.update(user)
        
        logger.info(f"Updated role for user {user.username} to {new_role.value}")
        log_role_changed(user.username, new_role.value, changed_by or "system")
        return True
    
    def deactivate_user(self, user_id: int, deactivated_by: str = None) -> bool:
        """Deactivate a user."""
        user = self.user_repository.get_by_id(user_id)
        if not user:
            return False
        
        # Prevent deactivating last admin
        if user.role == UserRole.ADMIN:
            admin_count = self.user_repository.count_by_role(UserRole.ADMIN)
            if admin_count <= 1:
                logger.warning("Cannot deactivate last admin user")
                return False
        
        self.user_repository.deactivate(user_id)
        logger.info(f"Deactivated user: {user.username}")
        log_user_deactivated(user.username, deactivated_by or "system")
        return True
    
    def validate_token(self, token: str) -> Optional[User]:
        """Validate access token and return user if valid."""
        payload = jwt_manager.verify_token(token, token_type="access")
        if not payload:
            return None
        
        user_id = int(payload.get("sub"))
        user = self.user_repository.get_by_id(user_id)
        
        if not user or not user.is_active:
            return None
        
        return user