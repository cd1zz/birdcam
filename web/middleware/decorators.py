"""Utility decorators combining authentication and IP restriction."""
from typing import Callable

from .auth import require_auth, require_admin
from .ip_restriction import require_internal_network


def require_admin_internal(func: Callable) -> Callable:
    """Require admin privileges from an internal network."""
    return require_internal_network(require_admin(func))


def require_auth_internal(func: Callable) -> Callable:
    """Require authenticated user from an internal network."""
    return require_internal_network(require_auth(func))
