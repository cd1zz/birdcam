# services/registration_service.py
from typing import Optional, Tuple
from datetime import datetime, timedelta
import secrets
from core.models import User, UserRole
from core.registration_models import RegistrationLink, RegistrationLinkType
from services.auth_service import AuthService
from services.email_service import EmailService
from database.repositories.user_repository import UserRepository
from database.repositories.registration_repository import RegistrationRepository
from config.email_config import EmailConfig
from utils.capture_logger import logger

class RegistrationService:
    def __init__(self, user_repo: UserRepository, reg_repo: RegistrationRepository, 
                 auth_service: AuthService, email_service: EmailService):
        self.user_repo = user_repo
        self.reg_repo = reg_repo
        self.auth_service = auth_service
        self.email_service = email_service
        self.config = EmailConfig.from_env()
    
    def register_user(self, username: str, password: str, email: str, 
                     registration_token: Optional[str] = None) -> Tuple[bool, str, Optional[User]]:
        """
        Register a new user
        Returns: (success, message, user)
        """
        # Check registration mode
        if self.config.registration_mode == 'disabled':
            return False, "Registration is currently disabled", None
        
        if self.config.registration_mode == 'invitation' and not registration_token:
            return False, "Registration requires an invitation link", None
        
        # Validate registration token if provided
        if registration_token:
            link = self.reg_repo.get_by_token(registration_token)
            if not link or not link.is_valid:
                return False, "Invalid or expired registration link", None
        
        # Validate email
        if not self.email_service.validate_email_address(email):
            return False, "Invalid email address", None
        
        # Check if email already exists
        if self.user_repo.get_by_email(email):
            return False, "Email address already registered", None
        
        # Check if username already exists
        if self.user_repo.get_by_username(username):
            return False, "Username already taken", None
        
        # Validate password
        is_valid, msg = self.email_service.validate_password(password)
        if not is_valid:
            return False, msg, None
        
        try:
            # Create user
            verification_token = self.email_service.generate_verification_token(email)
            verification_expires = datetime.now() + timedelta(hours=self.config.verification_expires_hours)
            
            user = self.auth_service.create_user(
                username=username,
                password=password,
                role=UserRole.VIEWER  # Default role for new registrations
            )
            
            # Update user with email info
            user.email = email
            user.email_verified = False
            user.verification_token = verification_token
            user.verification_token_expires = verification_expires
            self.user_repo.update(user)
            
            # Increment registration link usage
            if registration_token and link:
                self.reg_repo.increment_uses(link.id)
            
            # Send verification email
            base_url = self._get_base_url()
            verification_url = f"{base_url}/verify?token={verification_token}"
            self.email_service.send_verification_email(email, username, verification_url)
            
            logger.info(f"[REGISTRATION] New user registered: {username} ({email})")
            return True, "Registration successful! Please check your email to verify your account.", user
            
        except Exception as e:
            logger.error(f"[REGISTRATION] Failed to register user: {e}")
            return False, "Registration failed. Please try again.", None
    
    def verify_email(self, token: str) -> Tuple[bool, str]:
        """Verify user's email address"""
        email = self.email_service.verify_token(token)
        if not email:
            return False, "Invalid or expired verification token"
        
        user = self.user_repo.get_by_email(email)
        if not user:
            return False, "User not found"
        
        if user.email_verified:
            return True, "Email already verified"
        
        # Update user
        user.email_verified = True
        user.verification_token = None
        user.verification_token_expires = None
        self.user_repo.update(user)
        
        # Send welcome email
        self.email_service.send_welcome_email(user.email, user.username)
        
        logger.info(f"[REGISTRATION] Email verified for user: {user.username}")
        return True, "Email verified successfully!"
    
    def resend_verification(self, email: str) -> Tuple[bool, str]:
        """Resend verification email"""
        if not self.config.allow_resend_verification:
            return False, "Resending verification emails is disabled"
        
        user = self.user_repo.get_by_email(email)
        if not user:
            return False, "Email not found"
        
        if user.email_verified:
            return False, "Email already verified"
        
        # Generate new token
        verification_token = self.email_service.generate_verification_token(email)
        verification_expires = datetime.now() + timedelta(hours=self.config.verification_expires_hours)
        
        user.verification_token = verification_token
        user.verification_token_expires = verification_expires
        self.user_repo.update(user)
        
        # Send email
        base_url = self._get_base_url()
        verification_url = f"{base_url}/verify?token={verification_token}"
        self.email_service.send_verification_email(email, user.username, verification_url)
        
        return True, "Verification email sent"
    
    def create_registration_link(self, created_by: int, link_type: RegistrationLinkType,
                               max_uses: Optional[int] = None, 
                               expires_hours: Optional[int] = None) -> RegistrationLink:
        """Create a new registration link"""
        token = secrets.token_urlsafe(32)
        expires_at = None
        if expires_hours:
            expires_at = datetime.now() + timedelta(hours=expires_hours)
        
        link = RegistrationLink(
            id=None,
            token=token,
            link_type=link_type,
            max_uses=max_uses,
            uses=0,
            expires_at=expires_at,
            created_by=created_by,
            created_at=datetime.now(),
            is_active=True
        )
        
        link.id = self.reg_repo.create(link)
        logger.info(f"[REGISTRATION] Created registration link: {link_type.value}")
        return link
    
    def get_registration_url(self, token: str) -> str:
        """Get full registration URL for a token"""
        base_url = self._get_base_url()
        return f"{base_url}/register?token={token}"
    
    def cleanup_unverified_users(self):
        """Delete old unverified users"""
        if self.config.auto_delete_unverified_days <= 0:
            return
        
        cutoff_date = datetime.now() - timedelta(days=self.config.auto_delete_unverified_days)
        unverified_users = self.user_repo.get_unverified_users()
        
        for user in unverified_users:
            if user.created_at < cutoff_date:
                self.user_repo.delete(user.id)
                logger.info(f"[REGISTRATION] Deleted unverified user: {user.username}")
    
    def _get_base_url(self) -> str:
        """Get base URL for email links"""
        import os
        return os.getenv('APP_BASE_URL', 'http://localhost:5173')