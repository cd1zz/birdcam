"""Helper utilities for authentication-related functionality."""

from flask import current_app
from services.auth_service import AuthService
from database.repositories.user_repository import UserRepository
from database.connection import DatabaseManager


def get_auth_service() -> AuthService:
    """Return an :class:`AuthService` instance using the current app's database."""
    db_manager = DatabaseManager(current_app.config['DATABASE_PATH'])
    user_repository = UserRepository(db_manager)
    return AuthService(user_repository)
