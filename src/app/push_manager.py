"""
Push Notification Manager for F1 Betting Website.
Manages Web Push subscriptions stored in JSON files.

Structure of push_subscriptions.json:
{
  "subscriptions": {
    "username1": [
      {"endpoint": "...", "p256dh": "...", "auth": "..."},
      ...
    ],
    "username2": [...]
  }
}
"""

import json
import os
import tempfile
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .timezone_utils import timezone_utils

# Import pywebpush for sending notifications
try:
    import pywebpush
    from pywebpush import webpush
    PYWEBPOPUP_AVAILABLE = True
except ImportError:
    PYWEBPOPUP_AVAILABLE = False


class PushManager:
    """Manager for Web Push subscriptions stored in JSON."""

    def __init__(self, data_file: str = None):
        """
        Initialize PushManager.

        Args:
            data_file: Path to JSON file. Defaults to app/data/push_subscriptions.json
        """
        if data_file is None:
            script_dir = Path(__file__).parent
            data_file = script_dir / "data" / "push_subscriptions.json"

        self.data_file = Path(data_file)
        self._ensure_data_file_exists()

    def _logger(self):
        """Get logger instance."""
        try:
            from flask import current_app

            return current_app.logger
        except RuntimeError:
            return logging.getLogger(__name__)

    def _ensure_data_file_exists(self):
        """Ensure the push_subscriptions.json file exists with default structure."""
        if self.data_file.exists():
            return

        try:
            self.data_file.parent.mkdir(parents=True, exist_ok=True)

            default_data = {
                "subscriptions": {},
                "metadata": {
                    "created_at": timezone_utils.now_iso(),
                    "version": "1.0",
                },
            }

            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(default_data, f, indent=2)

            # Set restrictive permissions
            try:
                os.chmod(self.data_file, 0o600)
            except Exception:
                pass

            self._logger().info(
                "Created new push subscriptions file: %s", self.data_file
            )
        except Exception as e:
            self._logger().error("Error creating push subscriptions file: %s", e)
            raise

    def load_subscriptions(self) -> Dict:
        """Load all push subscriptions from file."""
        try:
            if not self.data_file.exists():
                self._ensure_data_file_exists()

            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            data.setdefault("subscriptions", {})
            self._logger().debug(
                "Loaded push subscriptions for %s users",
                len(data.get("subscriptions", {})),
            )
            return data
        except (json.JSONDecodeError, IOError) as e:
            self._logger().error("Error loading push subscriptions: %s", e)
            return {"subscriptions": {}}

    def save_subscriptions(self, data: Dict):
        """Save push subscriptions to file with atomic write."""
        backup_file = self.data_file.with_suffix(".bak")

        try:
            self.data_file.parent.mkdir(parents=True, exist_ok=True)

            # Create backup
            if self.data_file.exists():
                with open(self.data_file, "r", encoding="utf-8") as f:
                    backup_data = json.load(f)
                with open(backup_file, "w", encoding="utf-8") as f:
                    json.dump(backup_data, f, indent=2)

            # Save new data
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            self._logger().info(
                "Saved push subscriptions for %s users",
                len(data.get("subscriptions", {})),
            )

            # Remove backup
            if backup_file.exists():
                os.remove(backup_file)

        except Exception as e:
            self._logger().error("Error saving push subscriptions: %s", e)

            # Try to restore from backup
            if backup_file.exists():
                try:
                    with open(backup_file, "r", encoding="utf-8") as f:
                        restored_data = json.load(f)
                    with open(self.data_file, "w", encoding="utf-8") as f:
                        json.dump(restored_data, f, indent=2)
                    backup_file.unlink()
                    self._logger().error("Restored from backup after save failure")
                except Exception as restore_error:
                    self._logger().error(
                        "Failed to restore backup after save failure: %s", restore_error
                    )
            raise

    def add_subscription(
        self, username: str, endpoint: str, p256dh: str, auth: str
    ) -> bool:
        """
        Add a push subscription for a user.

        Args:
            username: The user's username
            endpoint: The push service endpoint URL
            p256dh: The P-256 DH key (base64url encoded)
            auth: The auth key (base64url encoded)

        Returns:
            True if subscription was added successfully
        """
        try:
            data = self.load_subscriptions()

            # Initialize user's subscription list if not exists
            data["subscriptions"].setdefault(username, [])

            # Check if this exact subscription already exists
            existing = next(
                (
                    s
                    for s in data["subscriptions"][username]
                    if s.get("endpoint") == endpoint
                ),
                None,
            )

            if existing:
                # Update existing subscription
                existing["p256dh"] = p256dh
                existing["auth"] = auth
                existing["updated_at"] = timezone_utils.now_iso()
                self._logger().debug("Updated existing subscription for %s", username)
            else:
                # Add new subscription
                data["subscriptions"][username].append(
                    {
                        "endpoint": endpoint,
                        "p256dh": p256dh,
                        "auth": auth,
                        "created_at": timezone_utils.now_iso(),
                        "updated_at": timezone_utils.now_iso(),
                    }
                )
                self._logger().info("Added new push subscription for %s", username)

            # Update metadata
            data.setdefault("metadata", {})
            data["metadata"]["updated_at"] = timezone_utils.now_iso()

            self.save_subscriptions(data)
            return True

        except Exception as e:
            self._logger().error("Error adding subscription for %s: %s", username, e)
            return False

    def remove_subscription(self, username: str, endpoint: str) -> bool:
        """
        Remove a specific subscription for a user.

        Args:
            username: The user's username
            endpoint: The push service endpoint to remove

        Returns:
            True if subscription was removed
        """
        try:
            data = self.load_subscriptions()

            if username not in data["subscriptions"]:
                return False

            # Filter out the subscription with matching endpoint
            original_count = len(data["subscriptions"][username])
            data["subscriptions"][username] = [
                s
                for s in data["subscriptions"][username]
                if s.get("endpoint") != endpoint
            ]

            # If user has no more subscriptions, remove the key
            if not data["subscriptions"][username]:
                del data["subscriptions"][username]

            if len(data["subscriptions"][username]) < original_count:
                # Update metadata
                data.setdefault("metadata", {})
                data["metadata"]["updated_at"] = timezone_utils.now_iso()

                self.save_subscriptions(data)
                self._logger().info("Removed push subscription for %s", username)
                return True

            return False

        except Exception as e:
            self._logger().error("Error removing subscription for %s: %s", username, e)
            return False

    def remove_all_subscriptions(self, username: str) -> int:
        """
        Remove all subscriptions for a user.

        Args:
            username: The user's username

        Returns:
            Number of subscriptions removed
        """
        try:
            data = self.load_subscriptions()

            if username not in data["subscriptions"]:
                return 0

            count = len(data["subscriptions"][username])
            del data["subscriptions"][username]

            # Update metadata
            data.setdefault("metadata", {})
            data["metadata"]["updated_at"] = timezone_utils.now_iso()

            self.save_subscriptions(data)
            self._logger().info("Removed %s push subscriptions for %s", count, username)
            return count

        except Exception as e:
            self._logger().error(
                "Error removing all subscriptions for %s: %s", username, e
            )
            return 0

    def get_user_subscriptions(self, username: str) -> List[Dict]:
        """
        Get all subscriptions for a specific user.

        Args:
            username: The user's username

        Returns:
            List of subscription dicts
        """
        try:
            data = self.load_subscriptions()
            return data.get("subscriptions", {}).get(username, [])
        except Exception as e:
            self._logger().error("Error getting subscriptions for %s: %s", username, e)
            return []

    def get_all_subscriptions(self) -> Dict:
        """Get all subscriptions for all users."""
        try:
            data = self.load_subscriptions()
            return data.get("subscriptions", {})
        except Exception as e:
            self._logger().error("Error getting all subscriptions: %s", e)
            return {}

    def count_subscriptions(self) -> int:
        """Count total number of subscriptions across all users."""
        try:
            data = self.load_subscriptions()
            return sum(len(subs) for subs in data.get("subscriptions", {}).values())
        except Exception as e:
            self._logger().error("Error counting subscriptions: %s", e)
            return 0

    def send_notification_to_all(self, title: str, body: str, data: Dict = None, url: str = None) -> Dict:
        """
        Send push notification to all subscribed users.

        Args:
            title: Notification title
            body: Notification body text
            data: Optional data dict to include in notification
            url: Optional URL to open when notification clicked

        Returns:
            dict: {'success': bool, 'sent': int, 'failed': int, 'errors': list}
        """
        if not PYWEBPOPUP_AVAILABLE:
            self._logger().error("pywebpush not available, cannot send notifications")
            return {"success": False, "sent": 0, "failed": 0, "error": "pywebpush not installed"}

        all_subscriptions = self.get_all_subscriptions()

        if not all_subscriptions:
            self._logger().info("No push subscriptions found, no notifications sent")
            return {"success": True, "sent": 0, "failed": 0, "message": "No active subscriptions"}

        sent_total = 0
        failed_total = 0
        errors_total = []

        # Get VAPID keys from environment
        import os as os_module
        private_key = os_module.environ.get("VAPID_PRIVATE_KEY")
        claim_email = os_module.environ.get("VAPID_CLAIM_EMAIL", "mailto:f1-betting@example.com")

        if not private_key:
            self._logger().error("VAPID_PRIVATE_KEY not configured, cannot send notifications")
            return {"success": False, "sent": 0, "failed": 0, "error": "VAPID_PRIVATE_KEY not configured"}

        payload = {
            "title": title,
            "body": body,
            "data": data or {},
            "url": url or "/",
        }

        for username, subscriptions in all_subscriptions.items():
            for subscription in subscriptions:
                try:
                    subscription_info = {
                        "endpoint": subscription["endpoint"],
                        "keys": {
                            "p256dh": subscription["p256dh"],
                            "auth": subscription["auth"],
                        },
                    }

                    webpush(
                        subscription_info=subscription_info,
                        data=json.dumps(payload),
                        vapid_private_key=private_key,
                        vapid_claims={"sub": claim_email},
                        ttl=3600,
                    )

                    sent_total += 1
                    self._logger().info(
                        f"Push notification sent to {username} at {subscription['endpoint']}"
                    )

                except Exception as e:
                    failed_total += 1
                    errors_total.append(f"{username}: {str(e)}")
                    self._logger().error(
                        f"Failed to send push notification to {username}: {e}"
                    )

        return {
            "success": failed_total == 0,
            "sent": sent_total,
            "failed": failed_total,
            "errors": errors_total,
        }


# Create a singleton instance
push_manager = PushManager()
