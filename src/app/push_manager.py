"""
Push Notification Manager for F1 Betting Website.
Manages Web Push subscriptions stored in JSON files via JsonStore.

Structure of push_subscriptions.json:
{
  "subscriptions": {
    "username1": [
      {"endpoint": "...", "p256dh": "...", "auth": "..."},
      ...
    ]
  }
}
"""

import json
import os
from pathlib import Path
from typing import Dict, List

from .core import JsonStore
from .core.logger import get_logger
from .timezone_utils import timezone_utils

try:
    import pywebpush
    from pywebpush import webpush

    PYWEBPUSH_AVAILABLE = True
except ImportError:
    PYWEBPUSH_AVAILABLE = False


class PushManager:
    """Manager for Web Push subscriptions stored in JSON."""

    def __init__(self, data_file: str = None):
        if data_file is None:
            data_file = Path(__file__).parent / "data" / "push_subscriptions.json"
        self._store = JsonStore(
            str(data_file),
            default={
                "subscriptions": {},
                "metadata": {
                    "created_at": timezone_utils.now_iso(),
                    "version": "1.0",
                },
            },
        )
        self._logger = get_logger(__name__)

    def _load(self) -> Dict:
        data = self._store.load()
        data.setdefault("subscriptions", {})
        return data

    def _save(self, data: Dict) -> None:
        self._store.save(data)

    # -- Subscription CRUD --------------------------------------------------

    def add_subscription(self, username: str, endpoint: str, p256dh: str, auth: str) -> bool:
        """Add or update a push subscription for a user."""
        try:
            data = self._load()
            subs = data["subscriptions"].setdefault(username, [])

            existing = next((s for s in subs if s.get("endpoint") == endpoint), None)
            if existing:
                existing["p256dh"] = p256dh
                existing["auth"] = auth
                existing["updated_at"] = timezone_utils.now_iso()
            else:
                subs.append({
                    "endpoint": endpoint,
                    "p256dh": p256dh,
                    "auth": auth,
                    "created_at": timezone_utils.now_iso(),
                    "updated_at": timezone_utils.now_iso(),
                })
                self._logger.info("Added push subscription for %s", username)

            data.setdefault("metadata", {})["updated_at"] = timezone_utils.now_iso()
            self._save(data)
            return True
        except Exception as e:
            self._logger.error("Error adding subscription for %s: %s", username, e)
            return False

    def remove_subscription(self, username: str, endpoint: str) -> bool:
        """Remove a specific subscription by endpoint."""
        try:
            data = self._load()
            if username not in data["subscriptions"]:
                return False

            subs = data["subscriptions"][username]
            data["subscriptions"][username] = [s for s in subs if s.get("endpoint") != endpoint]

            if not data["subscriptions"][username]:
                del data["subscriptions"][username]

            data.setdefault("metadata", {})["updated_at"] = timezone_utils.now_iso()
            self._save(data)
            self._logger.info("Removed push subscription for %s", username)
            return True
        except Exception as e:
            self._logger.error("Error removing subscription for %s: %s", username, e)
            return False

    def remove_all_subscriptions(self, username: str) -> int:
        """Remove all subscriptions for a user. Returns count removed."""
        try:
            data = self._load()
            if username not in data["subscriptions"]:
                return 0
            count = len(data["subscriptions"][username])
            del data["subscriptions"][username]
            data.setdefault("metadata", {})["updated_at"] = timezone_utils.now_iso()
            self._save(data)
            self._logger.info("Removed %d push subscriptions for %s", count, username)
            return count
        except Exception as e:
            self._logger.error("Error removing all subscriptions for %s: %s", username, e)
            return 0

    # -- Queries ------------------------------------------------------------

    def get_user_subscriptions(self, username: str) -> List[Dict]:
        return self._load().get("subscriptions", {}).get(username, [])

    def get_all_subscriptions(self) -> Dict[str, List[Dict]]:
        return self._load().get("subscriptions", {})

    def count_subscriptions(self) -> int:
        return sum(len(s) for s in self.get_all_subscriptions().values())

    # -- Sending ------------------------------------------------------------

    def send_to_all(self, title: str, body: str, data: Dict = None, url: str = None) -> Dict:
        """Send a push notification to all subscribed users."""
        if not PYWEBPUSH_AVAILABLE:
            return {"success": False, "sent": 0, "failed": 0, "error": "pywebpush not installed"}

        all_subs = self.get_all_subscriptions()
        if not all_subs:
            return {"success": True, "sent": 0, "failed": 0, "message": "No active subscriptions"}

        private_key = os.environ.get("VAPID_PRIVATE_KEY")
        claim = os.environ.get("VAPID_CLAIM_EMAIL", "mailto:f1-betting@example.com")
        if not private_key:
            return {"success": False, "sent": 0, "failed": 0, "error": "VAPID_PRIVATE_KEY not configured"}

        payload = json.dumps({"title": title, "body": body, "data": data or {}, "url": url or "/"})
        sent = failed = 0
        errors = []

        for username, subs in all_subs.items():
            for sub in subs:
                try:
                    webpush(
                        subscription_info={
                            "endpoint": sub["endpoint"],
                            "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
                        },
                        data=payload,
                        vapid_private_key=private_key,
                        vapid_claims={"sub": claim},
                        ttl=3600,
                    )
                    sent += 1
                except Exception as e:
                    failed += 1
                    errors.append(f"{username}: {e}")
                    self._logger.error("Push failed for %s: %s", username, e)

        return {"success": failed == 0, "sent": sent, "failed": failed, "errors": errors}


push_manager = PushManager()
