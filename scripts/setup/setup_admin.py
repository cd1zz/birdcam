#!/usr/bin/env python3
"""
BirdCam Admin Setup Script

This script helps create the initial admin account for the BirdCam system.
It should be run after the AI processor service is installed but before
first accessing the web interface.
"""

import os
import sys
import getpass
import re
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from database.connection import get_db_connection
    from database.repositories.user_repository import UserRepository
    from services.auth import AuthService
    from core.models import UserRole
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("\nPlease make sure you're in the project directory and have activated the virtual environment:")
    print("  cd /path/to/birdcam")
    print("  source .venv/bin/activate")
    print("  python scripts/setup/setup_admin.py")
    sys.exit(1)


def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_username(username):
    """Validate username format"""
    if len(username) < 3:
        return False, "Username must be at least 3 characters long"
    if len(username) > 50:
        return False, "Username must be less than 50 characters"
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False, "Username can only contain letters, numbers, hyphens, and underscores"
    return True, ""


def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    return True, ""


def main():
    """Main setup function"""
    print("=" * 60)
    print("BirdCam Admin Account Setup")
    print("=" * 60)
    print()
    
    # Check if we can connect to the database
    try:
        db = get_db_connection()
        user_repo = UserRepository(db)
        auth_service = AuthService(user_repo)
    except Exception as e:
        print(f"Error connecting to database: {e}")
        print("\nMake sure the AI processor service is configured and the database is accessible.")
        print("You may need to run the AI processor at least once to initialize the database.")
        sys.exit(1)
    
    # Check if admin already exists
    try:
        existing_admins = user_repo.get_users_by_role(UserRole.ADMIN)
        if existing_admins:
            print(f"Found {len(existing_admins)} existing admin account(s):")
            for admin in existing_admins:
                print(f"  - {admin.username} ({admin.email})")
            print()
            
            response = input("Create another admin account? [y/N]: ").strip().lower()
            if response != 'y':
                print("Setup cancelled.")
                return
    except Exception as e:
        print(f"Warning: Could not check for existing admins: {e}")
        response = input("Continue anyway? [Y/n]: ").strip().lower()
        if response == 'n':
            print("Setup cancelled.")
            return
    
    print("\nPlease provide the following information for the admin account:")
    print()
    
    # Get username
    while True:
        username = input("Username: ").strip()
        if not username:
            print("Username cannot be empty")
            continue
        
        valid, error = validate_username(username)
        if not valid:
            print(f"Invalid username: {error}")
            continue
        
        # Check if username exists
        try:
            if user_repo.get_by_username(username):
                print("Username already exists. Please choose another.")
                continue
        except:
            pass  # Database might not be initialized yet
        
        break
    
    # Get email
    while True:
        email = input("Email address: ").strip()
        if not email:
            print("Email cannot be empty")
            continue
        
        if not validate_email(email):
            print("Invalid email format")
            continue
        
        # Check if email exists
        try:
            if user_repo.get_by_email(email):
                print("Email already registered. Please use another.")
                continue
        except:
            pass  # Database might not be initialized yet
        
        break
    
    # Get password
    while True:
        password = getpass.getpass("Password (min 8 chars, mixed case, number): ")
        
        valid, error = validate_password(password)
        if not valid:
            print(f"Invalid password: {error}")
            continue
        
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Passwords do not match")
            continue
        
        break
    
    # Create the admin account
    print()
    print("Creating admin account...")
    
    try:
        # Create user with admin role
        user = auth_service.register_user(
            username=username,
            email=email,
            password=password,
            require_verification=False  # Admin doesn't need email verification
        )
        
        # Update role to admin
        user_repo.update_role(user.id, UserRole.ADMIN)
        
        print("✓ Admin account created successfully!")
        print()
        print("=" * 60)
        print("Setup complete!")
        print("=" * 60)
        print()
        print(f"Admin username: {username}")
        print(f"Admin email: {email}")
        print()
        print("You can now log in to the BirdCam web interface with these credentials.")
        print()
        print("The admin account has full access to:")
        print("  - System configuration")
        print("  - User management")
        print("  - All camera feeds and detections")
        print("  - System logs and monitoring")
        print()
        print("Make sure the AI processor service is running:")
        print("  sudo systemctl start ai-processor")
        print()
        print("Then access the web interface at:")
        print("  http://localhost:5001")
        print()
        print("=" * 60)
        
    except Exception as e:
        print(f"Error creating admin account: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure the database is initialized")
        print("2. Check that you're using the correct virtual environment")
        print("3. Verify the .env.processor file exists and is configured")
        print("4. Try running the AI processor once to initialize the database:")
        print("   python ai_processor/main.py")
        sys.exit(1)
    
    finally:
        # Close database connection
        try:
            db.close()
        except:
            pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)