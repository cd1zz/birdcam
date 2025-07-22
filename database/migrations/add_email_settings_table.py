#!/usr/bin/env python3
"""
Migration script to create email_settings table for configurable email settings
"""
import sqlite3
from pathlib import Path
import sys

def migrate_database(db_path: str):
    """Create email_settings table"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if table already exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='email_settings'")
        if cursor.fetchone() is None:
            print("Creating email_settings table...")
            
            cursor.execute("""
                CREATE TABLE email_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    
                    -- Provider selection
                    email_provider TEXT NOT NULL DEFAULT 'smtp',
                    
                    -- SMTP Settings
                    smtp_server TEXT,
                    smtp_port INTEGER,
                    smtp_username TEXT,
                    smtp_password TEXT,  -- Should be encrypted
                    smtp_use_tls BOOLEAN DEFAULT 1,
                    smtp_use_ssl BOOLEAN DEFAULT 0,
                    
                    -- Azure AD Settings
                    azure_tenant_id TEXT,
                    azure_client_id TEXT,
                    azure_client_secret TEXT,  -- Should be encrypted
                    azure_sender_email TEXT,
                    azure_use_shared_mailbox BOOLEAN DEFAULT 0,
                    
                    -- General Email Settings
                    from_email TEXT NOT NULL DEFAULT 'noreply@birdcam.local',
                    from_name TEXT NOT NULL DEFAULT 'BirdCam System',
                    
                    -- Template Settings
                    verification_subject TEXT NOT NULL DEFAULT 'Verify your BirdCam account',
                    verification_expires_hours INTEGER NOT NULL DEFAULT 48,
                    
                    -- Timestamps
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_by TEXT,
                    
                    -- Constraints
                    CHECK (email_provider IN ('smtp', 'azure'))
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX idx_email_provider ON email_settings(email_provider)")
            
            # Insert default record with environment variable values if available
            import os
            cursor.execute("""
                INSERT INTO email_settings (
                    email_provider,
                    smtp_server,
                    smtp_port,
                    smtp_username,
                    smtp_use_tls,
                    smtp_use_ssl,
                    azure_tenant_id,
                    azure_client_id,
                    azure_sender_email,
                    from_email,
                    from_name,
                    verification_subject,
                    verification_expires_hours
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
            print("Migration completed successfully!")
        else:
            print("email_settings table already exists, skipping migration.")
            
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    # Default database paths
    db_paths = [
        "/mnt/birdcam-storage/birdcam_processing/processing.db",
        "/data/birdcam_processor.db",
        "/data/birdcam_capture.db",
        "birdcam.db"  # Development database
    ]
    
    for db_path in db_paths:
        if Path(db_path).exists():
            print(f"Migrating database: {db_path}")
            migrate_database(db_path)