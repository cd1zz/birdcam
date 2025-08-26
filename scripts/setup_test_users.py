#!/usr/bin/env python3
"""Setup test users for E2E testing"""

import os
import sqlite3
from werkzeug.security import generate_password_hash

def setup_test_users(db_path='test.db'):
    """Create test users for E2E tests"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create users table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'viewer',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            verified BOOLEAN DEFAULT 1
        )
    ''')
    
    # Create test users
    test_users = [
        ('testuser', 'testpass', 'viewer'),
        ('admin', 'admin123', 'admin'),
        ('viewer', 'viewer123', 'viewer')
    ]
    
    for username, password, role in test_users:
        password_hash = generate_password_hash(password)
        try:
            cursor.execute(
                'INSERT INTO users (username, password_hash, role, verified) VALUES (?, ?, ?, 1)',
                (username, password_hash, role)
            )
            print(f"Created test user: {username} with role: {role}")
        except sqlite3.IntegrityError:
            print(f"User {username} already exists, skipping...")
    
    conn.commit()
    conn.close()
    print("Test users setup complete")

if __name__ == '__main__':
    db_path = os.environ.get('DATABASE_URL', 'sqlite:///test.db').replace('sqlite:///', '')
    setup_test_users(db_path)