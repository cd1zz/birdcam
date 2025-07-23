# web/routes/registration_routes.py
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from core.registration_models import RegistrationLinkType
from services.registration_service import RegistrationService
from services.email_service import EmailService
from database.repositories.email_settings_repository import EmailSettingsRepository
from database.repositories.email_template_repository import EmailTemplateRepository
from database.connection import DatabaseConnection
from web.middleware.auth import require_admin, require_auth, g
from web.middleware.ip_restriction import require_internal_network
from utils.capture_logger import logger
from core.email_template_model import EmailTemplateType
import json

def create_registration_routes(reg_service: RegistrationService, email_service: EmailService):
    reg_bp = Blueprint('registration', __name__)
    
    # Initialize repositories
    db_conn = DatabaseConnection()
    email_settings_repo = EmailSettingsRepository(db_conn)
    template_repo = EmailTemplateRepository(db_conn)
    
    # Combined decorator for admin + internal network
    def require_admin_internal(f):
        return require_internal_network(require_admin(f))
    
    @reg_bp.route('/api/register', methods=['POST'])
    def register():
        """Register a new user"""
        data = request.get_json()
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        email = data.get('email', '').strip()
        token = data.get('token')
        
        if not username or not password or not email:
            return jsonify({'error': 'Username, password, and email are required'}), 400
        
        success, message, user = reg_service.register_user(username, password, email, token)
        
        if success:
            return jsonify({
                'message': message,
                'username': user.username
            }), 201
        else:
            return jsonify({'error': message}), 400
    
    @reg_bp.route('/api/verify-email', methods=['POST'])
    def verify_email():
        """Verify email address"""
        data = request.get_json()
        token = data.get('token')
        
        if not token:
            return jsonify({'error': 'Verification token required'}), 400
        
        success, message = reg_service.verify_email(token)
        
        if success:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': message}), 400
    
    @reg_bp.route('/api/resend-verification', methods=['POST'])
    def resend_verification():
        """Resend verification email"""
        data = request.get_json()
        email = data.get('email', '').strip()
        
        if not email:
            return jsonify({'error': 'Email required'}), 400
        
        success, message = reg_service.resend_verification(email)
        
        if success:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': message}), 400
    
    # Admin endpoints with IP restriction
    @reg_bp.route('/api/admin/registration/generate-link', methods=['POST'])
    @require_admin_internal
    def generate_registration_link():
        """Generate a registration link (admin only, internal network)"""
        data = request.get_json()
        user = request.user
        
        link_type = data.get('link_type', 'single_use')
        max_uses = data.get('max_uses')
        expires_hours = data.get('expires_hours')
        
        try:
            link_type_enum = RegistrationLinkType(link_type)
        except ValueError:
            return jsonify({'error': 'Invalid link type'}), 400
        
        link = reg_service.create_registration_link(
            created_by=user.id,
            link_type=link_type_enum,
            max_uses=max_uses,
            expires_hours=expires_hours
        )
        
        return jsonify({
            'id': link.id,
            'token': link.token,
            'url': reg_service.get_registration_url(link.token),
            'link_type': link.link_type.value,
            'max_uses': link.max_uses,
            'expires_at': link.expires_at.isoformat() if link.expires_at else None
        }), 201
    
    @reg_bp.route('/api/admin/registration/links', methods=['GET'])
    @require_admin_internal
    def get_registration_links():
        """Get all registration links (admin only)"""
        links = reg_service.reg_repo.get_all_active()
        
        return jsonify([{
            'id': link.id,
            'token': link.token,
            'url': reg_service.get_registration_url(link.token),
            'link_type': link.link_type.value,
            'max_uses': link.max_uses,
            'uses': link.uses,
            'remaining_uses': link.remaining_uses,
            'expires_at': link.expires_at.isoformat() if link.expires_at else None,
            'created_at': link.created_at.isoformat(),
            'is_valid': link.is_valid
        } for link in links])
    
    @reg_bp.route('/api/admin/registration/links/<int:link_id>', methods=['DELETE'])
    @require_admin_internal
    def deactivate_link(link_id):
        """Deactivate a registration link (admin only)"""
        link = reg_service.reg_repo.get_by_id(link_id)
        if not link:
            return jsonify({'error': 'Link not found'}), 404
        
        reg_service.reg_repo.deactivate(link_id)
        return jsonify({'message': 'Link deactivated'}), 200
    
    @reg_bp.route('/api/admin/registration/pending', methods=['GET'])
    @require_admin_internal
    def get_pending_registrations():
        """Get unverified users (admin only)"""
        users = reg_service.user_repo.get_unverified_users()
        
        return jsonify([{
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'created_at': user.created_at.isoformat(),
            'verification_expires': user.verification_token_expires.isoformat() if user.verification_token_expires else None
        } for user in users])
    
    @reg_bp.route('/api/admin/registration/verify/<int:user_id>', methods=['POST'])
    @require_admin_internal
    def manually_verify_user(user_id):
        """Manually verify a user (admin only)"""
        user = reg_service.user_repo.get_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if user.email_verified:
            return jsonify({'message': 'Already verified'}), 200
        
        user.email_verified = True
        user.verification_token = None
        user.verification_token_expires = None
        reg_service.user_repo.update(user)
        
        # Send welcome email
        if user.email:
            email_service.send_welcome_email(user.email, user.username)
        
        return jsonify({'message': 'User verified'}), 200
    
    @reg_bp.route('/api/admin/email/test', methods=['POST'])
    @require_admin_internal
    def test_email():
        """Send a test email (admin only, internal network)"""
        data = request.get_json()
        to_email = data.get('email')
        
        if not to_email:
            return jsonify({'error': 'Email address required'}), 400
        
        success = email_service.send_email(
            to=to_email,
            subject="BirdCam Test Email",
            body="This is a test email from your BirdCam system. If you received this, your email configuration is working correctly!",
            html="<p>This is a test email from your BirdCam system.</p><p>If you received this, your email configuration is working correctly!</p>"
        )
        
        if success:
            return jsonify({'message': 'Test email sent successfully'}), 200
        else:
            return jsonify({'error': 'Failed to send test email. Check your SMTP configuration.'}), 500
    
    # Email configuration endpoints
    @reg_bp.route('/api/admin/settings/email', methods=['GET'])
    @require_admin_internal
    def get_email_settings():
        """Get email configuration (admin only)"""
        try:
            # Try to get from database first
            db_settings = email_settings_repo.get_settings()
            
            if db_settings:
                # Use database settings
                return jsonify({
                    'email_provider': db_settings.email_provider.value,
                    'smtp_server': db_settings.smtp_server,
                    'smtp_port': db_settings.smtp_port,
                    'smtp_username': db_settings.smtp_username,
                    'smtp_use_tls': db_settings.smtp_use_tls,
                    'smtp_use_ssl': db_settings.smtp_use_ssl,
                    'azure_tenant_id': db_settings.azure_tenant_id,
                    'azure_client_id': db_settings.azure_client_id,
                    'azure_sender_email': db_settings.azure_sender_email,
                    'azure_use_shared_mailbox': db_settings.azure_use_shared_mailbox,
                    'from_email': db_settings.from_email,
                    'from_name': db_settings.from_name,
                    'verification_subject': db_settings.verification_subject,
                    'verification_expires_hours': db_settings.verification_expires_hours,
                    'is_configured': email_service.config.is_email_configured(),
                    'has_smtp_password': bool(db_settings.smtp_password),
                    'has_azure_secret': bool(db_settings.azure_client_secret)
                })
            else:
                # Fall back to environment config
                config = email_service.config
                return jsonify({
                    'email_provider': config.email_provider,
                    'smtp_server': config.smtp_server,
                    'smtp_port': config.smtp_port,
                    'smtp_username': config.smtp_username,
                    'smtp_use_tls': config.use_tls,
                    'smtp_use_ssl': config.use_ssl,
                    'azure_tenant_id': config.azure_tenant_id,
                    'azure_client_id': config.azure_client_id,
                    'azure_sender_email': config.azure_sender_email,
                    'azure_use_shared_mailbox': config.azure_use_shared_mailbox,
                    'from_email': config.from_email,
                    'from_name': config.from_name,
                    'verification_subject': config.verification_subject,
                    'verification_expires_hours': config.verification_expires_hours,
                    'is_configured': config.is_email_configured(),
                    'has_smtp_password': bool(config.smtp_password),
                    'has_azure_secret': bool(config.azure_client_secret)
                })
        except Exception as e:
            logger.error(f"[EMAIL_SETTINGS] Error in get_email_settings endpoint: {e}")
            return jsonify({'error': 'Failed to retrieve email settings'}), 500
    
    @reg_bp.route('/api/admin/settings/email', methods=['PUT'])
    @require_admin_internal
    def update_email_settings():
        """Update email configuration (admin only)"""
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Get current user for audit trail
        current_user = g.user.username if hasattr(g, 'user') else 'system'
        
        # Validate email provider
        if 'email_provider' in data and data['email_provider'] not in ['smtp', 'azure']:
            return jsonify({'error': 'Invalid email provider'}), 400
        
        # Don't update passwords/secrets if they're empty strings
        if 'smtp_password' in data and data['smtp_password'] == '':
            del data['smtp_password']
        if 'azure_client_secret' in data and data['azure_client_secret'] == '':
            del data['azure_client_secret']
        
        # Update settings in database
        success = email_settings_repo.update_settings(data, current_user)
        
        if success:
            # Reload email service configuration
            email_service.reload_config()
            return jsonify({'message': 'Email settings updated successfully'}), 200
        else:
            return jsonify({'error': 'Failed to update email settings'}), 500
    
    @reg_bp.route('/api/admin/settings/registration', methods=['GET'])
    @require_admin_internal
    def get_registration_settings():
        """Get registration settings (admin only)"""
        config = email_service.config
        
        return jsonify({
            'registration_mode': config.registration_mode,
            'allow_resend_verification': config.allow_resend_verification,
            'auto_delete_unverified_days': config.auto_delete_unverified_days,
            'password_min_length': config.password_min_length,
            'password_require_uppercase': config.password_require_uppercase,
            'password_require_lowercase': config.password_require_lowercase,
            'password_require_numbers': config.password_require_numbers,
            'password_require_special': config.password_require_special
        })
    
    @reg_bp.route('/api/admin/settings/registration', methods=['PUT'])
    @require_admin_internal
    def update_registration_settings():
        """Update registration settings (admin only)"""
        try:
            data = request.get_json()
            
            # Validate registration mode
            if 'registration_mode' in data:
                valid_modes = ['disabled', 'open', 'invitation']
                if data['registration_mode'] not in valid_modes:
                    return jsonify({'error': f'Invalid registration mode. Must be one of: {", ".join(valid_modes)}'}), 400
            
            # Update settings in the email service config
            config = email_service.config
            
            # Update each setting if provided
            if 'registration_mode' in data:
                config.registration_mode = data['registration_mode']
                # Also update the app config for immediate effect
                current_app.config['REGISTRATION_MODE'] = data['registration_mode']
                current_app.config['REGISTRATION_ENABLED'] = data['registration_mode'] != 'disabled'
            
            if 'allow_resend_verification' in data:
                config.allow_resend_verification = bool(data['allow_resend_verification'])
                current_app.config['ALLOW_RESEND_VERIFICATION'] = config.allow_resend_verification
            
            if 'auto_delete_unverified_days' in data:
                config.auto_delete_unverified_days = int(data['auto_delete_unverified_days'])
                current_app.config['AUTO_DELETE_UNVERIFIED_DAYS'] = config.auto_delete_unverified_days
            
            if 'password_min_length' in data:
                config.password_min_length = max(6, int(data['password_min_length']))
                current_app.config['PASSWORD_MIN_LENGTH'] = config.password_min_length
            
            if 'password_require_uppercase' in data:
                config.password_require_uppercase = bool(data['password_require_uppercase'])
                current_app.config['PASSWORD_REQUIRE_UPPERCASE'] = config.password_require_uppercase
            
            if 'password_require_lowercase' in data:
                config.password_require_lowercase = bool(data['password_require_lowercase'])
                current_app.config['PASSWORD_REQUIRE_LOWERCASE'] = config.password_require_lowercase
            
            if 'password_require_numbers' in data:
                config.password_require_numbers = bool(data['password_require_numbers'])
                current_app.config['PASSWORD_REQUIRE_NUMBERS'] = config.password_require_numbers
            
            if 'password_require_special' in data:
                config.password_require_special = bool(data['password_require_special'])
                current_app.config['PASSWORD_REQUIRE_SPECIAL'] = config.password_require_special
            
            # Note: These settings are now stored in memory and will be reset on server restart
            # For permanent changes, consider storing in database or updating .env file
            
            return jsonify({
                'success': True,
                'message': 'Registration settings updated successfully',
                'warning': 'Settings will revert to .env values on server restart unless saved to database'
            })
            
        except ValueError as e:
            return jsonify({'error': f'Invalid value: {str(e)}'}), 400
        except Exception as e:
            logger.error(f"Failed to update registration settings: {e}")
            return jsonify({'error': 'Failed to update registration settings'}), 500
    
    @reg_bp.route('/api/admin/email/templates', methods=['GET'])
    @require_admin_internal
    def get_email_templates():
        """Get all email templates (admin only)"""
        try:
            templates = template_repo.get_all()
            return jsonify({
                'templates': [template.to_dict() for template in templates]
            })
        except Exception as e:
            logger.error(f"[EMAIL_TEMPLATES] Failed to get templates: {e}")
            return jsonify({'error': 'Failed to retrieve email templates'}), 500
    
    @reg_bp.route('/api/admin/email/templates/<template_type>', methods=['GET'])
    @require_admin_internal
    def get_email_template(template_type):
        """Get a specific email template (admin only)"""
        try:
            template_enum = EmailTemplateType(template_type)
            template = template_repo.get_by_type(template_enum)
            
            if template:
                return jsonify(template.to_dict())
            else:
                return jsonify({'error': 'Template not found'}), 404
        except ValueError:
            return jsonify({'error': 'Invalid template type'}), 400
        except Exception as e:
            logger.error(f"[EMAIL_TEMPLATES] Failed to get template: {e}")
            return jsonify({'error': 'Failed to retrieve email template'}), 500
    
    @reg_bp.route('/api/admin/email/templates/<template_type>', methods=['PUT'])
    @require_admin_internal
    def update_email_template(template_type):
        """Update an email template (admin only)"""
        try:
            data = request.get_json()
            
            # Validate template type
            try:
                template_enum = EmailTemplateType(template_type)
            except ValueError:
                return jsonify({'error': 'Invalid template type'}), 400
            
            # Get existing template
            template = template_repo.get_by_type(template_enum)
            if not template:
                return jsonify({'error': 'Template not found'}), 404
            
            # Update fields
            if 'subject' in data:
                template.subject = data['subject']
            if 'body_text' in data:
                template.body_text = data['body_text']
            if 'body_html' in data:
                template.body_html = data['body_html']
            if 'is_active' in data:
                template.is_active = data['is_active']
            
            # Save changes
            if template_repo.update(template):
                logger.info(f"[EMAIL_TEMPLATES] Updated template: {template_type}")
                return jsonify(template.to_dict())
            else:
                return jsonify({'error': 'Failed to update template'}), 500
                
        except Exception as e:
            logger.error(f"[EMAIL_TEMPLATES] Failed to update template: {e}")
            return jsonify({'error': str(e)}), 500
    
    @reg_bp.route('/api/admin/email/templates/<template_type>/reset', methods=['POST'])
    @require_admin_internal
    def reset_email_template(template_type):
        """Reset an email template to default (admin only)"""
        try:
            template_enum = EmailTemplateType(template_type)
            template = template_repo.reset_to_default(template_enum)
            
            if template:
                logger.info(f"[EMAIL_TEMPLATES] Reset template to default: {template_type}")
                return jsonify(template.to_dict())
            else:
                return jsonify({'error': 'Failed to reset template'}), 500
                
        except ValueError:
            return jsonify({'error': 'Invalid template type'}), 400
        except Exception as e:
            logger.error(f"[EMAIL_TEMPLATES] Failed to reset template: {e}")
            return jsonify({'error': str(e)}), 500
    
    @reg_bp.route('/api/admin/email/templates/<template_type>/preview', methods=['POST'])
    @require_admin_internal
    def preview_email_template(template_type):
        """Preview an email template with sample data (admin only)"""
        try:
            data = request.get_json()
            
            # Get sample variables based on template type
            sample_vars = {
                'verification': {
                    'username': 'John Doe',
                    'verification_url': 'https://example.com/verify?token=sample',
                    'expires_hours': 24
                },
                'welcome': {
                    'username': 'John Doe'
                },
                'password_reset': {
                    'username': 'John Doe',
                    'reset_url': 'https://example.com/reset?token=sample'
                },
                'registration_invite': {
                    'registration_url': 'https://example.com/register?token=sample',
                    'expires_hours': 48,
                    'message': 'Welcome to our bird monitoring community!'
                }
            }
            
            # Use provided variables or defaults
            variables = data.get('variables', sample_vars.get(template_type, {}))
            
            # Get template content
            if 'content' in data:
                # Preview custom content
                content = data['content']
                rendered = email_service._render_template(content, variables)
            else:
                # Preview saved template
                template_enum = EmailTemplateType(template_type)
                template = template_repo.get_by_type(template_enum)
                
                if not template:
                    return jsonify({'error': 'Template not found'}), 404
                
                rendered = email_service._render_template(
                    data.get('format', 'html') == 'html' and template.body_html or template.body_text,
                    variables
                )
            
            return jsonify({
                'preview': rendered,
                'variables': variables
            })
            
        except ValueError:
            return jsonify({'error': 'Invalid template type'}), 400
        except Exception as e:
            logger.error(f"[EMAIL_TEMPLATES] Failed to preview template: {e}")
            return jsonify({'error': str(e)}), 500
    
    @reg_bp.route('/api/admin/email/send-invite', methods=['POST'])
    @require_admin_internal
    def send_registration_invite():
        """Send a registration invitation email (admin only)"""
        try:
            data = request.get_json()
            to_email = data.get('email', '').strip()
            message = data.get('message', '').strip() or None
            
            if not to_email:
                return jsonify({'error': 'Email address is required'}), 400
            
            # Validate email
            if not email_service.validate_email_address(to_email):
                return jsonify({'error': 'Invalid email address'}), 400
            
            # Check registration mode
            if email_service.config.registration_mode == 'disabled':
                return jsonify({'error': 'Registration is currently disabled'}), 400
            
            # Generate registration link if in invitation mode
            registration_url = None
            expires_hours = None
            
            if email_service.config.registration_mode == 'invitation':
                # Generate a registration link
                link = reg_service.create_registration_link(
                    created_by=g.user.id,
                    link_type=RegistrationLinkType.SINGLE_USE,
                    max_uses=1,
                    expires_hours=48  # 48 hour expiration for email invites
                )
                
                if link:
                    # Build full URL (you may need to adjust this based on your frontend URL)
                    base_url = request.host_url.rstrip('/')
                    registration_url = f"{base_url}/register?token={link.token}"
                    expires_hours = 48
                else:
                    return jsonify({'error': 'Failed to generate registration link'}), 500
            else:
                # Open registration - just send the registration page URL
                base_url = request.host_url.rstrip('/')
                registration_url = f"{base_url}/register"
            
            # Send the invitation email
            success = email_service.send_registration_invite_email(
                to_email=to_email,
                registration_url=registration_url,
                expires_hours=expires_hours,
                message=message
            )
            
            if success:
                logger.info(f"[REGISTRATION] Sent invitation email to {to_email}")
                return jsonify({
                    'message': 'Invitation email sent successfully',
                    'email': to_email
                })
            else:
                return jsonify({'error': 'Failed to send invitation email'}), 500
                
        except Exception as e:
            logger.error(f"[REGISTRATION] Failed to send invitation: {e}")
            return jsonify({'error': str(e)}), 500
    
    return reg_bp