# database/repositories/email_settings_repository.py
from typing import Optional, Dict, Any
from datetime import datetime
from core.email_settings_model import EmailSettings, EmailProvider
from database.connection import DatabaseConnection
from utils.capture_logger import logger

class EmailSettingsRepository:
    def __init__(self, db: DatabaseConnection):
        self.db = db
    
    def get_settings(self) -> Optional[EmailSettings]:
        """Get email settings (should only be one record)"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if table exists
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='email_settings'
                """)
                if not cursor.fetchone():
                    logger.warning("[EMAIL_SETTINGS] Table does not exist")
                    return None
                
                cursor.execute("""
                    SELECT id, email_provider, smtp_server, smtp_port, smtp_username, 
                           smtp_password, smtp_use_tls, smtp_use_ssl,
                           azure_tenant_id, azure_client_id, azure_client_secret,
                           azure_sender_email, azure_use_shared_mailbox,
                           from_email, from_name, verification_subject,
                           verification_expires_hours, created_at, updated_at, updated_by
                    FROM email_settings
                    ORDER BY id DESC
                    LIMIT 1
                """)
                
                row = cursor.fetchone()
                if row:
                    return EmailSettings(
                        id=row[0],
                        email_provider=EmailProvider(row[1]),
                        smtp_server=row[2],
                        smtp_port=row[3],
                        smtp_username=row[4],
                        smtp_password=row[5],
                        smtp_use_tls=bool(row[6]),
                        smtp_use_ssl=bool(row[7]),
                        azure_tenant_id=row[8],
                        azure_client_id=row[9],
                        azure_client_secret=row[10],
                        azure_sender_email=row[11],
                        azure_use_shared_mailbox=bool(row[12]),
                        from_email=row[13],
                        from_name=row[14],
                        verification_subject=row[15],
                        verification_expires_hours=row[16],
                        created_at=datetime.fromisoformat(row[17]),
                        updated_at=datetime.fromisoformat(row[18]),
                        updated_by=row[19]
                    )
                return None
        except Exception as e:
            logger.error(f"[EMAIL_SETTINGS] Error getting settings: {e}")
            return None
    
    def update_settings(self, settings: Dict[str, Any], updated_by: str) -> bool:
        """Update email settings"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Build update query dynamically based on provided fields
            update_fields = []
            values = []
            
            # Map of setting keys to database columns
            field_mapping = {
                'email_provider': 'email_provider',
                'smtp_server': 'smtp_server',
                'smtp_port': 'smtp_port',
                'smtp_username': 'smtp_username',
                'smtp_password': 'smtp_password',
                'smtp_use_tls': 'smtp_use_tls',
                'smtp_use_ssl': 'smtp_use_ssl',
                'azure_tenant_id': 'azure_tenant_id',
                'azure_client_id': 'azure_client_id',
                'azure_client_secret': 'azure_client_secret',
                'azure_sender_email': 'azure_sender_email',
                'azure_use_shared_mailbox': 'azure_use_shared_mailbox',
                'from_email': 'from_email',
                'from_name': 'from_name',
                'verification_subject': 'verification_subject',
                'verification_expires_hours': 'verification_expires_hours'
            }
            
            for key, value in settings.items():
                if key in field_mapping:
                    update_fields.append(f"{field_mapping[key]} = ?")
                    values.append(value)
            
            if not update_fields:
                logger.warning("[EMAIL_SETTINGS] No valid fields to update")
                return False
            
            # Add updated_at and updated_by
            update_fields.append("updated_at = ?")
            values.append(datetime.now().isoformat())
            update_fields.append("updated_by = ?")
            values.append(updated_by)
            
            query = f"UPDATE email_settings SET {', '.join(update_fields)}"
            
            try:
                cursor.execute(query, values)
                conn.commit()
                logger.info(f"[EMAIL_SETTINGS] Settings updated by {updated_by}")
                return True
            except Exception as e:
                logger.error(f"[EMAIL_SETTINGS] Failed to update settings: {e}")
                conn.rollback()
                return False
    
    def create_table(self) -> bool:
        """Create email_settings table if it doesn't exist"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS email_settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email_provider TEXT NOT NULL DEFAULT 'smtp',
                        smtp_server TEXT,
                        smtp_port INTEGER,
                        smtp_username TEXT,
                        smtp_password TEXT,
                        smtp_use_tls BOOLEAN DEFAULT 1,
                        smtp_use_ssl BOOLEAN DEFAULT 0,
                        azure_tenant_id TEXT,
                        azure_client_id TEXT,
                        azure_client_secret TEXT,
                        azure_sender_email TEXT,
                        azure_use_shared_mailbox BOOLEAN DEFAULT 0,
                        from_email TEXT NOT NULL DEFAULT 'noreply@birdcam.local',
                        from_name TEXT NOT NULL DEFAULT 'BirdCam System',
                        verification_subject TEXT NOT NULL DEFAULT 'Verify your BirdCam account',
                        verification_expires_hours INTEGER NOT NULL DEFAULT 48,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_by TEXT,
                        CHECK (email_provider IN ('smtp', 'azure'))
                    )
                """)
                
                # Create index
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_email_provider ON email_settings(email_provider)")
                
                conn.commit()
                logger.info("[EMAIL_SETTINGS] Table created successfully")
                return True
        except Exception as e:
            logger.error(f"[EMAIL_SETTINGS] Failed to create table: {e}")
            return False
    
    def create_default_settings(self) -> bool:
        """Create default settings if none exist"""
        try:
            # Ensure table exists
            self.create_table()
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if settings already exist
                cursor.execute("SELECT COUNT(*) FROM email_settings")
                if cursor.fetchone()[0] > 0:
                    return True
                
                # Import environment settings
                import os
                cursor.execute("""
                    INSERT INTO email_settings (
                        email_provider, smtp_server, smtp_port, smtp_username,
                        smtp_use_tls, smtp_use_ssl, azure_tenant_id, azure_client_id,
                        azure_sender_email, from_email, from_name,
                        verification_subject, verification_expires_hours
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    os.getenv('EMAIL_PROVIDER', 'smtp'),
                    os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
                    int(os.getenv('SMTP_PORT', '587')),
                    os.getenv('SMTP_USERNAME'),
                    os.getenv('SMTP_USE_TLS', 'true').lower() == 'true',
                    os.getenv('SMTP_USE_SSL', 'false').lower() == 'true',
                    os.getenv('AZURE_TENANT_ID'),
                    os.getenv('AZURE_CLIENT_ID'),
                    os.getenv('AZURE_SENDER_EMAIL'),
                    os.getenv('EMAIL_FROM', 'noreply@birdcam.local'),
                    os.getenv('EMAIL_FROM_NAME', 'BirdCam System'),
                    os.getenv('EMAIL_VERIFICATION_SUBJECT', 'Verify your BirdCam account'),
                    int(os.getenv('VERIFICATION_EXPIRES_HOURS', '48'))
                ))
                conn.commit()
                logger.info("[EMAIL_SETTINGS] Created default settings from environment")
                return True
        except Exception as e:
            logger.error(f"[EMAIL_SETTINGS] Failed to create default settings: {e}")
            return False
    
    def encrypt_sensitive_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive fields before storing"""
        # TODO: Implement proper encryption for passwords/secrets
        # For now, just return as-is with a warning
        if 'smtp_password' in data or 'azure_client_secret' in data:
            logger.warning("[EMAIL_SETTINGS] Storing sensitive data - encryption should be implemented")
        return data
    
    def decrypt_sensitive_fields(self, settings: EmailSettings) -> EmailSettings:
        """Decrypt sensitive fields after retrieval"""
        # TODO: Implement proper decryption for passwords/secrets
        return settings