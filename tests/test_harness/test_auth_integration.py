"""Integration test harness for auth service"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from datetime import datetime
from core.models import User, UserRole
from database.connection import DatabaseManager
from database.repositories.user_repository import UserRepository
from services.auth_service import AuthService
from utils.auth import jwt_manager
import tempfile


def test_auth_service_integration():
    """Test the auth service with a real database"""
    print("Testing Auth Service Integration...")
    print("-" * 50)
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = Path(tmp.name)
    
    try:
        # Initialize database and repositories
        db_manager = DatabaseManager(db_path)
        user_repo = UserRepository(db_manager)
        user_repo.create_table()
        
        # Initialize auth service
        auth_service = AuthService(user_repo)
        
        # Test 1: Create users
        print("\n1. Testing user creation...")
        admin = auth_service.create_user("admin", "admin123", UserRole.ADMIN)
        assert admin is not None, "Failed to create admin user"
        print(f"   ✓ Created admin user: {admin.username}")
        
        viewer = auth_service.create_user("viewer", "viewer123", UserRole.VIEWER)
        assert viewer is not None, "Failed to create viewer user"
        print(f"   ✓ Created viewer user: {viewer.username}")
        
        # Test duplicate prevention
        duplicate = auth_service.create_user("ADMIN", "password", UserRole.VIEWER)
        assert duplicate is None, "Should not create duplicate user"
        print("   ✓ Duplicate prevention working")
        
        # Test 2: Authentication
        print("\n2. Testing authentication...")
        result = auth_service.authenticate("admin", "admin123")
        assert result is not None, "Authentication failed"
        user, access_token, refresh_token = result
        print(f"   ✓ Authenticated user: {user.username}")
        print(f"   ✓ Access token generated: {access_token[:20]}...")
        print(f"   ✓ Refresh token generated: {refresh_token[:20]}...")
        
        # Verify wrong password fails
        result = auth_service.authenticate("admin", "wrongpass")
        assert result is None, "Should not authenticate with wrong password"
        print("   ✓ Wrong password rejected")
        
        # Test 3: Token validation
        print("\n3. Testing token validation...")
        validated_user = auth_service.validate_token(access_token)
        assert validated_user is not None, "Token validation failed"
        assert validated_user.username == "admin", "Wrong user returned"
        print(f"   ✓ Token validated for user: {validated_user.username}")
        
        # Test 4: Token refresh
        print("\n4. Testing token refresh...")
        new_tokens = auth_service.refresh_tokens(refresh_token)
        assert new_tokens is not None, "Token refresh failed"
        new_access, new_refresh = new_tokens
        print("   ✓ Tokens refreshed successfully")
        
        # Verify new access token works
        validated_user = auth_service.validate_token(new_access)
        assert validated_user is not None, "New access token validation failed"
        print("   ✓ New access token is valid")
        
        # Test 5: Password update
        print("\n5. Testing password update...")
        success = auth_service.update_password(admin.id, "newadmin123")
        assert success, "Password update failed"
        print("   ✓ Password updated")
        
        # Verify old password no longer works
        result = auth_service.authenticate("admin", "admin123")
        assert result is None, "Old password should not work"
        print("   ✓ Old password rejected")
        
        # Verify new password works
        result = auth_service.authenticate("admin", "newadmin123")
        assert result is not None, "New password should work"
        print("   ✓ New password accepted")
        
        # Test 6: Role management
        print("\n6. Testing role management...")
        success = auth_service.update_role(viewer.id, UserRole.ADMIN)
        assert success, "Role update failed"
        print("   ✓ Viewer promoted to admin")
        
        # Try to remove last admin (should fail)
        success = auth_service.update_role(admin.id, UserRole.VIEWER)
        assert success, "Should allow admin demotion when multiple admins exist"
        print("   ✓ Admin demoted (multiple admins exist)")
        
        # Now try to remove the last admin
        success = auth_service.update_role(viewer.id, UserRole.VIEWER)
        assert not success, "Should not remove last admin"
        print("   ✓ Last admin protection working")
        
        # Test 7: User deactivation
        print("\n7. Testing user deactivation...")
        # Create another user to deactivate
        test_user = auth_service.create_user("testuser", "test123", UserRole.VIEWER)
        success = auth_service.deactivate_user(test_user.id)
        assert success, "Deactivation failed"
        print("   ✓ User deactivated")
        
        # Verify deactivated user can't authenticate
        result = auth_service.authenticate("testuser", "test123")
        assert result is None, "Deactivated user should not authenticate"
        print("   ✓ Deactivated user cannot authenticate")
        
        print("\n" + "="*50)
        print("All auth service integration tests passed! ✓")
        
    finally:
        # Cleanup
        if db_path.exists():
            db_path.unlink()
            print(f"\nCleaned up temporary database: {db_path}")


if __name__ == "__main__":
    test_auth_service_integration()