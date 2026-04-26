import json
import os
import hashlib
import secrets
import tempfile
import shutil
import logging
from flask import current_app


def load_users():
    """Load users from JSON file."""
    users_file = os.path.join(os.path.dirname(__file__), "data", "users.json")
    if not os.path.exists(users_file):
        return {}
    try:
        with open(users_file, "r", encoding="utf-8") as f:
            return json.load(f).get("users", {})
    except (json.JSONDecodeError, IOError):
        return {}


def save_users(users):
    """Save users to JSON file with atomic write."""
    users_file = os.path.join(os.path.dirname(__file__), "data", "users.json")
    data_dir = os.path.dirname(users_file)

    os.makedirs(data_dir, exist_ok=True)

    temp_fd, temp_path = tempfile.mkstemp(dir=data_dir, prefix="users_")
    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
            json.dump({"users": users}, f, indent=2)

        # Set restrictive permissions
        try:
            os.chmod(temp_path, 0o600)
        except Exception:
            pass

        # Atomic replace
        shutil.move(temp_path, users_file)

        try:
            os.chmod(users_file, 0o600)
        except Exception:
            pass
    except Exception:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


def hash_password(password):
    """Hash password using PBKDF2"""
    salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
    )
    return f"pbkdf2_sha256${salt}${hashed.hex()}"


def verify_password(stored_password, provided_password):
    """Verify password against stored hash"""
    if not stored_password.startswith("pbkdf2_sha256$"):
        # Old plaintext password - migrate on next login
        return stored_password == provided_password

    _, salt, hashed = stored_password.split("$")
    new_hash = hashlib.pbkdf2_hmac(
        "sha256", provided_password.encode("utf-8"), salt.encode("utf-8"), 100000
    )
    return new_hash.hex() == hashed


def ensure_first_admin():
    """Ensure there's at least one admin user (first user becomes admin)"""
    users = load_users()

    if not users:
        return users

    # Promote first user to admin if no admins exist
    if not any(user.get("is_admin", False) for user in users.values()):
        first_username = next(iter(users.keys()))
        users[first_username]["is_admin"] = True
        save_users(users)

    return users
