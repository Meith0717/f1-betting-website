"""
Event scheduler — one-time timed events on a background thread.

Schedules race notifications (qualifying start, race start, 1h-before-race)
and fires them at the right time. Message content lives in NotificationService.
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional

from .core.logger import get_logger
from .timezone_utils import timezone_utils


class EventManager:
    """Schedules and triggers one-time events on a background thread."""

    def __init__(self, check_interval: int = 10):
        self.check_interval = check_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._events: Dict[str, Dict] = {}
        self._lock = threading.Lock()
        self._logger = get_logger(__name__)

    def schedule_event(
        self,
        event_id: str,
        trigger_time: datetime,
        callback: Callable[[str, Dict], None],
        data: Dict = None,
    ) -> bool:
        """Schedule a one-time event. trigger_time must be timezone-aware."""
        if trigger_time.tzinfo is None:
            raise ValueError("trigger_time must be timezone-aware (UTC)")

        with self._lock:
            if event_id in self._events:
                self._logger.warning("Event %s already exists", event_id)
                return False
            self._events[event_id] = {
                "trigger_time": trigger_time,
                "callback": callback,
                "data": data or {},
            }
            return True

    def schedule_race_notifications(self, race: Dict) -> None:
        """Schedule qualifying/race/1h-before notifications for a race."""
        from .race_data_manager import race_data_manager
        from .services.notification_service import notification_service

        race_id = race.get("id")
        if not race_id:
            return

        race_name = race.get("name", race_id)
        sessions = race.get("sessions", [])
        now = timezone_utils.utc_now()

        def _schedule(event_suffix: str, session: Dict, offset: str, session_type: str):
            dt = race_data_manager.get_session_datetime(session)
            if dt > now:
                self.schedule_event(
                    f"{event_suffix}_{race_id}",
                    dt,
                    lambda eid, d: notification_service.send_race_notification(d),
                    {
                        "race_id": race_id,
                        "race_name": race_name,
                        "session_type": session_type,
                        "offset": offset,
                    },
                )

        qualifying = next((s for s in sessions if s.get("type") == "Qualifying"), None)
        if qualifying:
            _schedule("qualifying_start", qualifying, "start", "Qualifying")

        race_session = next((s for s in sessions if s.get("type") == "Race"), None)
        if race_session:
            _schedule("race_start", race_session, "start", "Race")
            one_hour_before = race_data_manager.get_session_datetime(race_session) - timedelta(hours=1)
            if one_hour_before > now:
                self.schedule_event(
                    f"race_1h_before_{race_id}",
                    one_hour_before,
                    lambda eid, d: notification_service.send_race_notification(d),
                    {
                        "race_id": race_id,
                        "race_name": race_name,
                        "session_type": "Race",
                        "offset": "1h_before",
                    },
                )

    def schedule_all_race_notifications(self) -> int:
        """Schedule notifications for all non-canceled races. Returns race count."""
        from .race_data_manager import race_data_manager

        count = 0
        for race in race_data_manager.get_all_races():
            if not race.get("canceled"):
                self.schedule_race_notifications(race)
                count += 1
        return count

    def _check_events(self) -> None:
        """Trigger all due events and remove them."""
        now = timezone_utils.utc_now()
        due = []
        with self._lock:
            for event_id, event in list(self._events.items()):
                if event["trigger_time"] <= now:
                    due.append((event_id, event))

        for event_id, event in due:
            try:
                event["callback"](event_id, event["data"])
            except Exception as e:
                self._logger.error("Error triggering event %s: %s", event_id, e)
            with self._lock:
                self._events.pop(event_id, None)

    def _run(self) -> None:
        self._logger.info("Event manager started, checking every %ds", self.check_interval)
        while self._running:
            try:
                self._check_events()
            except Exception as e:
                self._logger.error("Event manager error: %s", e)
            time.sleep(self.check_interval)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        self._logger.info("Event manager stopped")


event_manager = EventManager()
