"""
User account management service.

Consolidates all user CRUD operations that were previously split between
auth_utils.py and BettingManager.load_users/save_users/_update_user_scores.
"""

import hashlib
import os
import secrets
from datetime import datetime
from typing import Dict, Optional

import pytz

from ..core import JsonStore, get_logger


class UserService:
    """Manages user accounts stored in JSON."""

    def __init__(self, data_file: str = None):
        if data_file is None:
            data_file = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "data", "users.json"
            )
        self._store = JsonStore(data_file, default={"users": {}})
        self._logger = get_logger(__name__)

    # -- Password helpers --------------------------------------------------

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using PBKDF2+SHA256."""
        salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
        )
        return f"pbkdf2_sha256${salt}${hashed.hex()}"

    @staticmethod
    def verify_password(stored_password: str, provided_password: str) -> bool:
        """Verify a password against a stored hash (supports legacy plaintext)."""
        if not stored_password.startswith("pbkdf2_sha256$"):
            return stored_password == provided_password
        _, salt, hashed = stored_password.split("$")
        new_hash = hashlib.pbkdf2_hmac(
            "sha256",
            provided_password.encode("utf-8"),
            salt.encode("utf-8"),
            100000,
        )
        return new_hash.hex() == hashed

    # -- CRUD ---------------------------------------------------------------

    def load_all(self) -> Dict[str, dict]:
        """Load all users as {username: user_data}."""
        return self._store.load().get("users", {})

    def save_all(self, users: Dict[str, dict]) -> None:
        """Save all users."""
        self._store.save({"users": users})

    def get(self, username: str) -> Optional[dict]:
        """Get a single user by username."""
        return self.load_all().get(username)

    def exists(self, username: str) -> bool:
        return username in self.load_all()

    def create(
        self,
        username: str,
        password: str,
        is_admin: bool = False,
    ) -> dict:
        """Create a new user and return the user dict."""
        users = self.load_all()
        user = {
            "password": self.hash_password(password),
            "score": 0,
            "created_at": datetime.now(pytz.UTC).isoformat(),
            "last_login": None,
            "is_admin": is_admin,
        }
        users[username] = user
        self.save_all(users)
        return user

    def update(self, username: str, **fields) -> bool:
        """Update fields on an existing user. Returns False if user not found."""
        users = self.load_all()
        if username not in users:
            return False
        users[username].update(fields)
        self.save_all(users)
        return True

    def delete(self, username: str) -> bool:
        """Delete a user. Returns False if not found."""
        users = self.load_all()
        if username not in users:
            return False
        del users[username]
        self.save_all(users)
        return True

    def record_login(self, username: str) -> None:
        """Update last_login timestamp."""
        self.update(username, last_login=datetime.now(pytz.UTC).isoformat())

    def migrate_password(self, username: str, plaintext_password: str) -> None:
        """Migrate a legacy plaintext password to a hashed one."""
        self.update(username, password=self.hash_password(plaintext_password))

    # -- Scoring ------------------------------------------------------------

    def add_score(self, username: str, points: int, race_id: str) -> bool:
        """Add points to a user's score and record in score_history."""
        users = self.load_all()
        if username not in users:
            self._logger.warning("User not found for score update: %s", username)
            return False

        current = users[username].get("score", 0)
        users[username]["score"] = current + points
        users[username].setdefault("score_history", []).append(
            {
                "race_id": race_id,
                "points": points,
                "total": current + points,
                "timestamp": datetime.now(pytz.UTC).isoformat(),
            }
        )
        self.save_all(users)
        self._logger.info(
            "Score updated for %s: %s -> %s (+%s)",
            username, current, current + points, points,
        )
        return True

    def reset_all_scores(self) -> None:
        """Reset every user's score to 0."""
        users = self.load_all()
        for user in users.values():
            user["score"] = 0
        self.save_all(users)

    # -- Admin helpers ------------------------------------------------------

    def count_admins(self) -> int:
        """Count how many users have admin privileges."""
        return sum(1 for u in self.load_all().values() if u.get("is_admin", False))

    def ensure_first_admin(self) -> Dict[str, dict]:
        """Promote the first user to admin if no admins exist."""
        users = self.load_all()
        if users and not any(u.get("is_admin", False) for u in users.values()):
            first = next(iter(users))
            users[first]["is_admin"] = True
            self.save_all(users)
        return users

    def get_leaderboard(self) -> list:
        """Return users sorted by score descending as (username, user_data) tuples."""
        users = self.load_all()
        return sorted(users.items(), key=lambda x: x[1].get("score", 0), reverse=True)

    def get_rank(self, username: str) -> Optional[int]:
        """Get a user's 1-based rank on the leaderboard."""
        leaderboard = self.get_leaderboard()
        for i, (name, _) in enumerate(leaderboard):
            if name == username:
                return i + 1
        return None


# Singleton
user_service = UserService()
