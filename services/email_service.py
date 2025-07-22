# services/email_service.py
from flask_mail import Mail, Message
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import secrets
import re
from email_validator import validate_email, EmailNotValidError
from config.email_config import EmailConfig
from utils.capture_logger import logger
from services.azure_email_provider import AzureEmailProvider
from database.repositories.email_settings_repository import EmailSettingsRepository
from database.repositories.email_template_repository import EmailTemplateRepository
from database.connection import DatabaseConnection
from core.email_settings_model import EmailProvider as EmailProviderEnum
from core.email_template_model import EmailTemplateType

class EmailService:
    def __init__(self, app=None, config: Optional[EmailConfig] = None):
        self.mail = Mail()
        self.config = config or EmailConfig.from_env()
        self.serializer = None
        self.azure_provider = None
        self.app = None
        
        # Initialize database connection for settings
        self.db_conn = DatabaseConnection()
        self.settings_repo = EmailSettingsRepository(self.db_conn)
        self.template_repo = EmailTemplateRepository(self.db_conn)
        
        # Ensure email_settings table exists and has default data
        self.settings_repo.create_default_settings()
        
        # Load configuration from database if available
        self._load_config_from_db()
        
        # Initialize Azure provider if configured
        if self.config.email_provider == 'azure' and self.config.is_azure_configured():
            self.azure_provider = AzureEmailProvider(
                tenant_id=self.config.azure_tenant_id,
                client_id=self.config.azure_client_id,
                client_secret=self.config.azure_client_secret,
                sender_email=self.config.azure_sender_email,
                use_shared_mailbox=self.config.azure_use_shared_mailbox
            )
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize Flask-Mail with app"""
        self.app = app  # Store app reference for reloading
        
        # Configure Flask-Mail
        app.config.update(
            MAIL_SERVER=self.config.smtp_server,
            MAIL_PORT=self.config.smtp_port,
            MAIL_USERNAME=self.config.smtp_username,
            MAIL_PASSWORD=self.config.smtp_password,
            MAIL_USE_TLS=self.config.use_tls,
            MAIL_USE_SSL=self.config.use_ssl,
            MAIL_DEFAULT_SENDER=(self.config.from_name, self.config.from_email)
        )
        
        self.mail.init_app(app)
        self.serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    
    def send_email(self, to: str, subject: str, body: str, html: Optional[str] = None) -> bool:
        """Send an email using configured provider"""
        if not self.config.is_email_configured():
            logger.warning("[EMAIL] Email not configured, skipping email send")
            return False
        
        if self.config.email_provider == 'azure' and self.azure_provider:
            # Use Azure Graph API
            try:
                return self.azure_provider.send_email(
                    to=to,
                    subject=subject,
                    body=body,
                    html=html
                )
            except Exception as e:
                logger.error(f"[EMAIL] Azure send failed: {e}")
                return False
        else:
            # Use SMTP
            try:
                msg = Message(
                    subject=subject,
                    recipients=[to],
                    body=body,
                    html=html
                )
                self.mail.send(msg)
                logger.info(f"[EMAIL] Sent email to {to} via SMTP")
                return True
            except Exception as e:
                logger.error(f"[EMAIL] SMTP send failed: {e}")
                return False
    
    def generate_verification_token(self, email: str) -> str:
        """Generate a verification token for email"""
        return self.serializer.dumps(email, salt='email-verify')
    
    def verify_token(self, token: str, max_age: Optional[int] = None) -> Optional[str]:
        """Verify a token and return the email if valid"""
        if max_age is None:
            max_age = self.config.verification_expires_hours * 3600
        
        try:
            email = self.serializer.loads(token, salt='email-verify', max_age=max_age)
            return email
        except SignatureExpired:
            logger.warning("[EMAIL] Verification token expired")
            return None
        except BadSignature:
            logger.warning("[EMAIL] Invalid verification token")
            return None
    
    def generate_reset_token(self, email: str) -> str:
        """Generate a password reset token"""
        return self.serializer.dumps(email, salt='password-reset')
    
    def verify_reset_token(self, token: str, max_age: int = 3600) -> Optional[str]:
        """Verify a reset token (default 1 hour expiry)"""
        try:
            email = self.serializer.loads(token, salt='password-reset', max_age=max_age)
            return email
        except (SignatureExpired, BadSignature):
            return None
    
    def validate_email_address(self, email: str) -> bool:
        """Validate email format and deliverability"""
        try:
            validate_email(email, check_deliverability=False)
            return True
        except EmailNotValidError:
            return False
    
    def validate_password(self, password: str) -> tuple[bool, str]:
        """Validate password against configured requirements"""
        if len(password) < self.config.password_min_length:
            return False, f"Password must be at least {self.config.password_min_length} characters"
        
        if self.config.password_require_uppercase and not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        
        if self.config.password_require_lowercase and not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        
        if self.config.password_require_numbers and not re.search(r'\d', password):
            return False, "Password must contain at least one number"
        
        if self.config.password_require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain at least one special character"
        
        return True, "Password is valid"
    
    def _render_template(self, template_content: str, variables: Dict[str, Any]) -> str:
        """Render template with variables using simple replacement"""
        rendered = template_content
        for key, value in variables.items():
            # Handle both {{variable}} and {{ variable }} formats
            rendered = rendered.replace(f'{{{{{key}}}}}', str(value))
            rendered = rendered.replace(f'{{{{ {key} }}}}', str(value))
        
        # Handle conditional blocks (simple implementation)
        # {{#if variable}}content{{/if}}
        import re
        if_pattern = r'\{\{#if\s+(\w+)\}\}(.*?)\{\{/if\}\}'
        
        def replace_if_block(match):
            var_name = match.group(1)
            content = match.group(2)
            if var_name in variables and variables[var_name]:
                return content
            return ''
        
        rendered = re.sub(if_pattern, replace_if_block, rendered, flags=re.DOTALL)
        
        return rendered
    
    def send_verification_email(self, user_email: str, username: str, verification_url: str) -> bool:
        """Send email verification message using template"""
        # Try to get active template
        template = self.template_repo.get_active_by_type(EmailTemplateType.VERIFICATION)
        
        if template:
            # Use template
            variables = {
                'username': username,
                'verification_url': verification_url,
                'expires_hours': self.config.verification_expires_hours
            }
            
            subject = self._render_template(template.subject, variables)
            body = self._render_template(template.body_text, variables)
            html = self._render_template(template.body_html, variables)
        else:
            # Fallback to hardcoded template
            subject = self.config.verification_subject
            
            body = f"""Hello {username},

Welcome to BirdCam! Please verify your email address by clicking the link below:

{verification_url}

This link will expire in {self.config.verification_expires_hours} hours.

If you didn't create this account, please ignore this email.

Best regards,
The BirdCam Team"""
            
            html = f"""<html>
<body>
    <h2>Welcome to BirdCam!</h2>
    <p>Hello {username},</p>
    <p>Please verify your email address by clicking the button below:</p>
    <p style="text-align: center; margin: 30px 0;">
        <a href="{verification_url}" style="background-color: #4CAF50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px;">
            Verify Email Address
        </a>
    </p>
    <p>Or copy and paste this link into your browser:</p>
    <p>{verification_url}</p>
    <p><small>This link will expire in {self.config.verification_expires_hours} hours.</small></p>
    <p>If you didn't create this account, please ignore this email.</p>
    <p>Best regards,<br>The BirdCam Team</p>
</body>
</html>"""
        
        return self.send_email(user_email, subject, body, html)
    
    def send_welcome_email(self, user_email: str, username: str) -> bool:
        """Send welcome email after verification using template"""
        # Try to get active template
        template = self.template_repo.get_active_by_type(EmailTemplateType.WELCOME)
        
        if template:
            # Use template
            variables = {
                'username': username
            }
            
            subject = self._render_template(template.subject, variables)
            body = self._render_template(template.body_text, variables)
            html = self._render_template(template.body_html, variables)
        else:
            # Fallback to hardcoded template
            subject = "Welcome to BirdCam!"
            
            body = f"""Hello {username},

Your email has been verified successfully! You can now log in to your BirdCam account.

Enjoy monitoring your bird visitors!

Best regards,
The BirdCam Team"""
            
            html = f"""<html>
<body>
    <h2>Welcome to BirdCam!</h2>
    <p>Hello {username},</p>
    <p>Your email has been verified successfully! You can now log in to your BirdCam account.</p>
    <p>Enjoy monitoring your bird visitors!</p>
    <p>Best regards,<br>The BirdCam Team</p>
</body>
</html>"""
        
        return self.send_email(user_email, subject, body, html)
    
    def send_password_reset_email(self, user_email: str, username: str, reset_url: str) -> bool:
        """Send password reset email"""
        subject = "Reset your BirdCam password"
        
        body = f"""Hello {username},

You requested to reset your password. Click the link below to set a new password:

{reset_url}

This link will expire in 1 hour.

If you didn't request this, please ignore this email. Your password will remain unchanged.

Best regards,
The BirdCam Team"""
        
        html = f"""<html>
<body>
    <h2>Reset Your Password</h2>
    <p>Hello {username},</p>
    <p>You requested to reset your password. Click the button below to set a new password:</p>
    <p style="text-align: center; margin: 30px 0;">
        <a href="{reset_url}" style="background-color: #f44336; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px;">
            Reset Password
        </a>
    </p>
    <p>Or copy and paste this link into your browser:</p>
    <p>{reset_url}</p>
    <p><small>This link will expire in 1 hour.</small></p>
    <p>If you didn't request this, please ignore this email. Your password will remain unchanged.</p>
    <p>Best regards,<br>The BirdCam Team</p>
</body>
</html>"""
        
        return self.send_email(user_email, subject, body, html)
    def _load_config_from_db(self):
        """Load configuration from database if available"""
        try:
            db_settings = self.settings_repo.get_settings()
            if db_settings:
                # Override config with database values
                self.config.email_provider = db_settings.email_provider.value
                self.config.smtp_server = db_settings.smtp_server or self.config.smtp_server
                self.config.smtp_port = db_settings.smtp_port or self.config.smtp_port
                self.config.smtp_username = db_settings.smtp_username or self.config.smtp_username
                self.config.smtp_password = db_settings.smtp_password or self.config.smtp_password
                self.config.use_tls = db_settings.smtp_use_tls
                self.config.use_ssl = db_settings.smtp_use_ssl
                self.config.azure_tenant_id = db_settings.azure_tenant_id or self.config.azure_tenant_id
                self.config.azure_client_id = db_settings.azure_client_id or self.config.azure_client_id
                self.config.azure_client_secret = db_settings.azure_client_secret or self.config.azure_client_secret
                self.config.azure_sender_email = db_settings.azure_sender_email or self.config.azure_sender_email
                self.config.azure_use_shared_mailbox = db_settings.azure_use_shared_mailbox
                self.config.from_email = db_settings.from_email
                self.config.from_name = db_settings.from_name
                self.config.verification_subject = db_settings.verification_subject
                self.config.verification_expires_hours = db_settings.verification_expires_hours
                logger.info("[EMAIL] Loaded configuration from database")
        except Exception as e:
            logger.warning(f"[EMAIL] Failed to load config from database: {e}, using environment config")
    
    def reload_config(self):
        """Reload configuration from database and reinitialize providers"""
        self._load_config_from_db()
        
        # Reinitialize Azure provider if needed
        if self.config.email_provider == 'azure' and self.config.is_azure_configured():
            self.azure_provider = AzureEmailProvider(
                tenant_id=self.config.azure_tenant_id,
                client_id=self.config.azure_client_id,
                client_secret=self.config.azure_client_secret,
                sender_email=self.config.azure_sender_email,
                use_shared_mailbox=self.config.azure_use_shared_mailbox
            )
        else:
            self.azure_provider = None
        
        # Reinitialize Flask-Mail if app is available
        if self.app:
            self.app.config.update(
                MAIL_SERVER=self.config.smtp_server,
                MAIL_PORT=self.config.smtp_port,
                MAIL_USERNAME=self.config.smtp_username,
                MAIL_PASSWORD=self.config.smtp_password,
                MAIL_USE_TLS=self.config.use_tls,
                MAIL_USE_SSL=self.config.use_ssl,
                MAIL_DEFAULT_SENDER=(self.config.from_name, self.config.from_email)
            )
        
        logger.info("[EMAIL] Configuration reloaded")
    
    def send_registration_invite_email(self, to_email: str, registration_url: str, 
                                     expires_hours: Optional[int] = None, 
                                     message: Optional[str] = None) -> bool:
        """Send registration invitation email using template"""
        # Try to get active template
        template = self.template_repo.get_active_by_type(EmailTemplateType.REGISTRATION_INVITE)
        
        if template:
            # Use template
            variables = {
                'registration_url': registration_url,
                'expires_hours': expires_hours,
                'message': message
            }
            
            subject = self._render_template(template.subject, variables)
            body = self._render_template(template.body_text, variables)
            html = self._render_template(template.body_html, variables)
        else:
            # Fallback to simple template
            subject = "You're invited to join BirdCam"
            
            expires_text = f"\n\nThis invitation will expire in {expires_hours} hours." if expires_hours else ""
            message_text = f"\n\nPersonal message from the administrator:\n{message}" if message else ""
            
            body = f"""Hello,

You've been invited to join BirdCam, a bird monitoring system.

To register your account, please click the link below:

{registration_url}{expires_text}{message_text}

Best regards,
The BirdCam Team"""
            
            html = f"""<html>
<body>
    <h2>You're invited to join BirdCam</h2>
    <p>Hello,</p>
    <p>You've been invited to join BirdCam, a bird monitoring system.</p>
    <p>To register your account, please click the button below:</p>
    <p style="text-align: center; margin: 30px 0;">
        <a href="{registration_url}" style="background-color: #3498db; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px;">
            Register Account
        </a>
    </p>
    <p>Or copy and paste this link into your browser:</p>
    <p>{registration_url}</p>
    {'<p><small>This invitation will expire in ' + str(expires_hours) + ' hours.</small></p>' if expires_hours else ''}
    {'<div style="background-color: #ecf0f1; padding: 15px; border-radius: 4px; margin: 20px 0;"><p style="margin: 0;"><strong>Personal message from the administrator:</strong></p><p style="margin: 10px 0 0 0;">' + message + '</p></div>' if message else ''}
    <p>Best regards,<br>The BirdCam Team</p>
</body>
</html>"""
        
        return self.send_email(to_email, subject, body, html)
