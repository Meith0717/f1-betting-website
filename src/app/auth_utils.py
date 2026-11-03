"""
Authentication utilities — thin wrapper over UserService.

Preserves the module-level function API used by routes and decorators
while delegating all work to services/user_service.py.
"""

import os

from .services.user_service import user_service


def get_registration_password() -> str:
    """Get the current registration password from environment variable."""
    return os.environ.get("REGISTRATION_PASSWORD", "f1betting2024")


def load_users():
    """Load all users as {username: user_data}."""
    return user_service.load_all()


def save_users(users):
    """Save all users."""
    user_service.save_all(users)


def hash_password(password):
    return user_service.hash_password(password)


def verify_password(stored_password, provided_password):
    return user_service.verify_password(stored_password, provided_password)


def ensure_first_admin():
    """Ensure there's at least one admin user."""
    return user_service.ensure_first_admin()
