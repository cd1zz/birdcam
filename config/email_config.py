# config/email_config.py
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class EmailConfig:
    """Email configuration settings"""
    # Email Provider Selection
    email_provider: str  # 'smtp' or 'azure'
    
    # SMTP Settings
    smtp_server: str
    smtp_port: int
    smtp_username: Optional[str]
    smtp_password: Optional[str]
    use_tls: bool
    use_ssl: bool
    
    # Azure AD Settings
    azure_tenant_id: Optional[str]
    azure_client_id: Optional[str]
    azure_client_secret: Optional[str]
    azure_sender_email: Optional[str]
    azure_use_shared_mailbox: bool
    
    # Email Settings
    from_email: str
    from_name: str
    
    # Template Settings
    verification_subject: str
    verification_expires_hours: int
    
    # Registration Settings
    registration_mode: str  # 'open', 'invitation', 'disabled'
    allow_resend_verification: bool
    auto_delete_unverified_days: int
    
    # Password Requirements
    password_min_length: int
    password_require_uppercase: bool
    password_require_lowercase: bool
    password_require_numbers: bool
    password_require_special: bool
    
    @classmethod
    def from_env(cls) -> 'EmailConfig':
        """Load configuration from environment variables"""
        return cls(
            # Email Provider Selection
            email_provider=os.getenv('EMAIL_PROVIDER', 'smtp'),
            
            # SMTP Settings
            smtp_server=os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            smtp_port=int(os.getenv('SMTP_PORT', '587')),
            smtp_username=os.getenv('SMTP_USERNAME'),
            smtp_password=os.getenv('SMTP_PASSWORD'),
            use_tls=os.getenv('SMTP_USE_TLS', 'true').lower() == 'true',
            use_ssl=os.getenv('SMTP_USE_SSL', 'false').lower() == 'true',
            
            # Azure AD Settings
            azure_tenant_id=os.getenv('AZURE_TENANT_ID'),
            azure_client_id=os.getenv('AZURE_CLIENT_ID'),
            azure_client_secret=os.getenv('AZURE_CLIENT_SECRET'),
            azure_sender_email=os.getenv('AZURE_SENDER_EMAIL'),
            azure_use_shared_mailbox=os.getenv('AZURE_USE_SHARED_MAILBOX', 'false').lower() == 'true',
            
            # Email Settings
            from_email=os.getenv('EMAIL_FROM', 'noreply@birdcam.local'),
            from_name=os.getenv('EMAIL_FROM_NAME', 'BirdCam System'),
            
            # Template Settings
            verification_subject=os.getenv('EMAIL_VERIFICATION_SUBJECT', 'Verify your BirdCam account'),
            verification_expires_hours=int(os.getenv('VERIFICATION_EXPIRES_HOURS', '48')),
            
            # Registration Settings
            registration_mode=os.getenv('REGISTRATION_MODE', 'invitation'),
            allow_resend_verification=os.getenv('ALLOW_RESEND_VERIFICATION', 'true').lower() == 'true',
            auto_delete_unverified_days=int(os.getenv('AUTO_DELETE_UNVERIFIED_DAYS', '7')),
            
            # Password Requirements
            password_min_length=int(os.getenv('PASSWORD_MIN_LENGTH', '8')),
            password_require_uppercase=os.getenv('PASSWORD_REQUIRE_UPPERCASE', 'true').lower() == 'true',
            password_require_lowercase=os.getenv('PASSWORD_REQUIRE_LOWERCASE', 'true').lower() == 'true',
            password_require_numbers=os.getenv('PASSWORD_REQUIRE_NUMBERS', 'true').lower() == 'true',
            password_require_special=os.getenv('PASSWORD_REQUIRE_SPECIAL', 'true').lower() == 'true',
        )
    
    def is_smtp_configured(self) -> bool:
        """Check if SMTP settings are properly configured"""
        return bool(self.smtp_server and self.smtp_port)
    
    def is_azure_configured(self) -> bool:
        """Check if Azure AD settings are properly configured"""
        return bool(self.azure_tenant_id and self.azure_client_id and self.azure_client_secret)
    
    def is_email_configured(self) -> bool:
        """Check if any email provider is configured"""
        if self.email_provider == 'azure':
            return self.is_azure_configured()
        else:
            return self.is_smtp_configured()