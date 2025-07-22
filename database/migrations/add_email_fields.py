#!/usr/bin/env python3
"""
Migration script to add email fields to existing users table
"""
import sqlite3
from pathlib import Path
import sys

def migrate_database(db_path: str):
    """Add email fields to users table"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'email' not in columns:
            print("Adding email fields to users table...")
            
            # Add new columns without UNIQUE constraint first
            cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
            cursor.execute("ALTER TABLE users ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT 0")
            cursor.execute("ALTER TABLE users ADD COLUMN verification_token TEXT")
            cursor.execute("ALTER TABLE users ADD COLUMN verification_token_expires TIMESTAMP")
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_email ON users(email)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_verification_token ON users(verification_token)")
            
            conn.commit()
            print("Migration completed successfully!")
        else:
            print("Email fields already exist, skipping migration.")
            
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