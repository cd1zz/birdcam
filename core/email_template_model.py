# core/email_template_model.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum

class EmailTemplateType(Enum):
    VERIFICATION = "verification"
    WELCOME = "welcome"
    PASSWORD_RESET = "password_reset"
    REGISTRATION_INVITE = "registration_invite"

@dataclass
class EmailTemplate:
    id: Optional[int] = None
    template_type: EmailTemplateType = EmailTemplateType.VERIFICATION
    subject: str = ""
    body_text: str = ""
    body_html: str = ""
    variables: str = ""  # JSON string of available variables
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self):
        return {
            'id': self.id,
            'template_type': self.template_type.value,
            'subject': self.subject,
            'body_text': self.body_text,
            'body_html': self.body_html,
            'variables': self.variables,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_row(cls, row):
        if not row:
            return None
        return cls(
            id=row[0],
            template_type=EmailTemplateType(row[1]),
            subject=row[2],
            body_text=row[3],
            body_html=row[4],
            variables=row[5],
            is_active=row[6],
            created_at=datetime.fromisoformat(row[7]) if row[7] else None,
            updated_at=datetime.fromisoformat(row[8]) if row[8] else None
        )

# Default templates
DEFAULT_TEMPLATES = {
    EmailTemplateType.VERIFICATION: {
        'subject': 'Verify your BirdCam email address',
        'body_text': '''Hello {{username}},

Welcome to BirdCam! Please verify your email address by clicking the link below:

{{verification_url}}

This link will expire in {{expires_hours}} hours.

If you didn't create this account, please ignore this email.

Best regards,
The BirdCam Team''',
        'body_html': '''<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2c3e50;">Welcome to BirdCam!</h2>
        <p>Hello {{username}},</p>
        <p>Please verify your email address by clicking the button below:</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{{verification_url}}" style="background-color: #4CAF50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">
                Verify Email Address
            </a>
        </div>
        <p>Or copy and paste this link into your browser:</p>
        <p style="word-break: break-all; color: #3498db;">{{verification_url}}</p>
        <p><small style="color: #7f8c8d;">This link will expire in {{expires_hours}} hours.</small></p>
        <p>If you didn't create this account, please ignore this email.</p>
        <p>Best regards,<br>The BirdCam Team</p>
    </div>
</body>
</html>''',
        'variables': '{"username": "User\'s display name", "verification_url": "Email verification URL", "expires_hours": "Hours until link expires"}'
    },
    EmailTemplateType.WELCOME: {
        'subject': 'Welcome to BirdCam!',
        'body_text': '''Hello {{username}},

Your email has been verified successfully! You can now log in to your BirdCam account.

Enjoy monitoring your bird visitors!

Best regards,
The BirdCam Team''',
        'body_html': '''<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2c3e50;">Welcome to BirdCam!</h2>
        <p>Hello {{username}},</p>
        <p>Your email has been verified successfully! You can now log in to your BirdCam account.</p>
        <p>Enjoy monitoring your bird visitors!</p>
        <p>Best regards,<br>The BirdCam Team</p>
    </div>
</body>
</html>''',
        'variables': '{"username": "User\'s display name"}'
    },
    EmailTemplateType.PASSWORD_RESET: {
        'subject': 'Reset your BirdCam password',
        'body_text': '''Hello {{username}},

You requested to reset your password. Click the link below to set a new password:

{{reset_url}}

This link will expire in 1 hour.

If you didn't request this, please ignore this email. Your password will remain unchanged.

Best regards,
The BirdCam Team''',
        'body_html': '''<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2c3e50;">Reset Your Password</h2>
        <p>Hello {{username}},</p>
        <p>You requested to reset your password. Click the button below to set a new password:</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{{reset_url}}" style="background-color: #f44336; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">
                Reset Password
            </a>
        </div>
        <p>Or copy and paste this link into your browser:</p>
        <p style="word-break: break-all; color: #3498db;">{{reset_url}}</p>
        <p><small style="color: #7f8c8d;">This link will expire in 1 hour.</small></p>
        <p>If you didn't request this, please ignore this email. Your password will remain unchanged.</p>
        <p>Best regards,<br>The BirdCam Team</p>
    </div>
</body>
</html>''',
        'variables': '{"username": "User\'s display name", "reset_url": "Password reset URL"}'
    },
    EmailTemplateType.REGISTRATION_INVITE: {
        'subject': 'You\'re invited to join BirdCam',
        'body_text': '''Hello,

You've been invited to join BirdCam, a bird monitoring system.

To register your account, please click the link below:

{{registration_url}}

{{#if expires_hours}}This invitation will expire in {{expires_hours}} hours.{{/if}}

{{#if message}}
Personal message from the administrator:
{{message}}
{{/if}}

Best regards,
The BirdCam Team''',
        'body_html': '''<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2c3e50;">You're invited to join BirdCam</h2>
        <p>Hello,</p>
        <p>You've been invited to join BirdCam, a bird monitoring system.</p>
        <p>To register your account, please click the button below:</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{{registration_url}}" style="background-color: #3498db; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">
                Register Account
            </a>
        </div>
        <p>Or copy and paste this link into your browser:</p>
        <p style="word-break: break-all; color: #3498db;">{{registration_url}}</p>
        {{#if expires_hours}}
        <p><small style="color: #7f8c8d;">This invitation will expire in {{expires_hours}} hours.</small></p>
        {{/if}}
        {{#if message}}
        <div style="background-color: #ecf0f1; padding: 15px; border-radius: 4px; margin: 20px 0;">
            <p style="margin: 0;"><strong>Personal message from the administrator:</strong></p>
            <p style="margin: 10px 0 0 0;">{{message}}</p>
        </div>
        {{/if}}
        <p>Best regards,<br>The BirdCam Team</p>
    </div>
</body>
</html>''',
        'variables': '{"registration_url": "Registration URL", "expires_hours": "Hours until link expires (optional)", "message": "Personal message from admin (optional)"}'
    }
}