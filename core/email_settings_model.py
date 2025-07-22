# core/email_settings_model.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum

class EmailProvider(Enum):
    SMTP = "smtp"
    AZURE = "azure"

@dataclass
class EmailSettings:
    """Email settings stored in database"""
    id: Optional[int]
    
    # Provider selection
    email_provider: EmailProvider
    
    # SMTP Settings
    smtp_server: Optional[str]
    smtp_port: Optional[int]
    smtp_username: Optional[str]
    smtp_password: Optional[str]  # Should be encrypted
    smtp_use_tls: bool
    smtp_use_ssl: bool
    
    # Azure AD Settings
    azure_tenant_id: Optional[str]
    azure_client_id: Optional[str]
    azure_client_secret: Optional[str]  # Should be encrypted
    azure_sender_email: Optional[str]
    azure_use_shared_mailbox: bool
    
    # General Email Settings
    from_email: str
    from_name: str
    
    # Template Settings
    verification_subject: str
    verification_expires_hours: int
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    updated_by: Optional[str]  # Username who last updated
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()