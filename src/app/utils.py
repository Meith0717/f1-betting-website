import json
import os
import hashlib
import secrets
import tempfile
import shutil


def load_users():
    """Load users from JSON file with error handling"""
    users_file = os.path.join(os.path.dirname(__file__), "data", "users.json")
    if not os.path.exists(users_file):
        return {}
    try:
        with open(users_file, "r") as f:
            data = json.load(f)
            return data.get("users", {})
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading users: {e}")
        return {}


def save_users(users):
    """Save users to JSON file with atomic write and security checks"""
    users_file = os.path.join(os.path.dirname(__file__), "data", "users.json")

    try:
        # Create data directory with restrictive permissions
        os.makedirs(os.path.dirname(users_file), exist_ok=True)

        # Set restrictive permissions on data directory (if possible)
        try:
            os.chmod(os.path.dirname(users_file), 0o700)
        except:
            pass  # Permission change may fail on some systems

        # Write to temp file first
        temp_fd, temp_path = tempfile.mkstemp(
            dir=os.path.dirname(users_file), prefix="users_"
        )
        with os.fdopen(temp_fd, "w") as f:
            json.dump({"users": users}, f, indent=2)

        # Set restrictive permissions on temp file
        try:
            os.chmod(temp_path, 0o600)
        except:
            pass

        # Atomic replace
        shutil.move(temp_path, users_file)

        # Set restrictive permissions on final file
        try:
            os.chmod(users_file, 0o600)
        except:
            pass
    except Exception as e:
        print(f"Error saving users: {e}")
        if "temp_path" in locals() and os.path.exists(temp_path):
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

    # If no users exist, this is first run - make first user admin
    if not users:
        return users

    # If users exist but no admins, make the first user admin
    if not any(user.get("is_admin", False) for user in users.values()):
        first_username = next(iter(users.keys()))
        users[first_username]["is_admin"] = True
        save_users(users)

    return users
