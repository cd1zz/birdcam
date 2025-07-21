#!/usr/bin/env python3
"""
Setup initial admin user for the bird detection system
"""
import sys
import os
import getpass
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.models import UserRole
from database.connection import DatabaseManager
from database.repositories.user_repository import UserRepository
from services.auth_service import AuthService

# Load environment variables
load_dotenv()

def setup_admin_user(db_path: Path):
    """Create initial admin user"""
    print("\n🔐 Bird Detection System - Admin Setup")
    print("=" * 40)
    
    # Initialize services
    db_manager = DatabaseManager(db_path)
    user_repo = UserRepository(db_manager)
    auth_service = AuthService(user_repo)
    
    # Create user table
    print("📊 Creating user table...")
    user_repo.create_table()
    
    # Check if admin already exists
    existing_admins = user_repo.count_by_role(UserRole.ADMIN)
    if existing_admins > 0:
        print(f"⚠️  {existing_admins} admin user(s) already exist.")
        response = input("Do you want to create another admin? (y/n): ").lower()
        if response != 'y':
            print("Exiting...")
            return
    
    # Get admin credentials
    print("\n👤 Create Admin User")
    while True:
        username = input("Username: ").strip()
        if len(username) < 3:
            print("❌ Username must be at least 3 characters")
            continue
        
        # Check if username exists
        if user_repo.get_by_username(username):
            print("❌ Username already exists")
            continue
        break
    
    while True:
        password = getpass.getpass("Password: ")
        if len(password) < 6:
            print("❌ Password must be at least 6 characters")
            continue
        
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("❌ Passwords don't match")
            continue
        break
    
    # Create admin user
    print("\n🔨 Creating admin user...")
    user = auth_service.create_user(username, password, UserRole.ADMIN)
    
    if user:
        print(f"✅ Admin user '{username}' created successfully!")
        print("\n📝 You can now log in to the web interface with these credentials.")
    else:
        print("❌ Failed to create admin user")
        sys.exit(1)

def main():
    """Main entry point"""
    # Determine which database to use
    if len(sys.argv) > 1 and sys.argv[1] == '--capture':
        # Setup for capture/Pi system
        storage_path = Path(os.getenv('STORAGE_PATH', './bird_footage'))
        camera_id = int(os.getenv('CAMERA_IDS', '0').split(',')[0])
        db_path = storage_path / f"camera_{camera_id}" / "capture.db"
        print(f"Setting up admin for capture system (camera {camera_id})")
    else:
        # Default to processing server
        storage_path = Path(os.getenv('STORAGE_PATH', './bird_processing'))
        db_path = storage_path / "processing.db"
        print("Setting up admin for processing server")
    
    # Ensure database directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Setup admin
    setup_admin_user(db_path)
    
    print("\n🎉 Setup complete!")
    print("You can create additional users through the web interface.")
    print("\nTo create a viewer user, use the web interface or run:")
    print("  python setup_admin.py --viewer")

if __name__ == "__main__":
    main()