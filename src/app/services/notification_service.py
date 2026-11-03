"""
Notification service — builds race notification messages and dispatches them.

Extracted from EventManager so the scheduler only handles timing, not
message content.
"""

from typing import Dict

from ..core.logger import get_logger


class NotificationService:
    """Builds and sends race-related push notifications."""

    def __init__(self, push_manager=None):
        self._logger = get_logger(__name__)
        self._push = push_manager  # injected to avoid circular import

    def set_push_manager(self, push_manager) -> None:
        self._push = push_manager

    @staticmethod
    def build_message(data: Dict) -> tuple:
        """
        Build (title, body) for a race notification event.

        Args:
            data: Event data with race_name, session_type, offset

        Returns:
            (title, body) tuple
        """
        race_name = data.get("race_name", data.get("race_id", "Unknown"))
        session_type = data.get("session_type", "Session")
        offset = data.get("offset", "")

        if offset == "start":
            if session_type == "Qualifying":
                return f"{session_type} Starting Now", f"{race_name} {session_type} is starting."
            return f"{session_type} Starting Now", f"{race_name} race is starting NOW!"
        if offset == "1h_before":
            return f"Last Chance to Bet - {race_name}", "Race starts in 1 hour. Place your bets now before it's too late!"
        return f"F1 Notification: {race_name}", f"{session_type} event for {race_name}"

    def send_race_notification(self, data: Dict) -> bool:
        """Build the message from event data and broadcast via push."""
        if not self._push:
            return False
        title, body = self.build_message(data)
        result = self._push.send_to_all(title, body)
        if not result.get("success") and result.get("failed", 0) > 0:
            self._logger.warning("Failed to send push notification: %s", title)
        return result.get("success", False)


notification_service = NotificationService()
