import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional, Any

from .timezone_utils import timezone_utils


class EventManager:
    """Manages time-based event scheduling and triggering."""

    def __init__(self, check_interval: int = 10):
        """
        Initialize the EventManager.

        Args:
            check_interval: Seconds between checks for due events
        """
        self.check_interval = check_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._events: Dict[str, Dict] = {}
        self._lock = threading.Lock()
        self._logger = logging.getLogger(__name__)

    def schedule_event(
        self,
        event_id: str,
        trigger_time: datetime,
        callback: Callable[[str, Dict], None],
        data: Dict = None,
    ) -> bool:
        """
        Schedule a one-time event.

        Args:
            event_id: Unique identifier for the event
            trigger_time: UTC datetime when to trigger (MUST be timezone-aware)
            callback: Function to call when event triggers.
                      Signature: callback(event_id: str, data: Dict)
            data: Optional data to pass to callback

        Returns:
            True if scheduled successfully, False if event_id already exists

        Raises:
            ValueError: If trigger_time is not timezone-aware
        """
        if trigger_time.tzinfo is None:
            raise ValueError(
                "trigger_time must be timezone-aware. "
                "Use timezone_utils to create UTC datetimes, e.g., "
                "timezone_utils.utc_now() or race_data_manager.get_session_datetime()"
            )

        with self._lock:
            if event_id in self._events:
                self._logger.warning(f"Event {event_id} already exists")
                return False

            self._events[event_id] = {
                "trigger_time": trigger_time,
                "callback": callback,
                "data": data or {},
                "triggered": False,
            }
            self._logger.info(
                f"Scheduled event {event_id} for {trigger_time.isoformat()}"
            )
            return True

    def schedule_recurring(
        self,
        event_id: str,
        start_time: datetime,
        interval: timedelta,
        callback: Callable[[str, Dict], None],
        data: Dict = None,
    ) -> bool:
        """
        Schedule a recurring event.

        Args:
            event_id: Unique identifier
            start_time: First trigger UTC datetime (MUST be timezone-aware)
            interval: Time between triggers (timedelta)
            callback: Function to call when event triggers
            data: Optional data to pass to callback

        Returns:
            True if scheduled successfully, False if event_id already exists

        Raises:
            ValueError: If start_time is not timezone-aware
        """
        if start_time.tzinfo is None:
            raise ValueError(
                "start_time must be timezone-aware. "
                "Use timezone_utils to create UTC datetimes, e.g., "
                "timezone_utils.utc_now() or race_data_manager.get_session_datetime()"
            )

        with self._lock:
            if event_id in self._events:
                self._logger.warning(f"Event {event_id} already exists")
                return False

            self._events[event_id] = {
                "start_time": start_time,
                "interval": interval,
                "next_trigger": start_time,
                "callback": callback,
                "data": data or {},
                "recurring": True,
            }
            self._logger.info(
                f"Scheduled recurring event {event_id} starting {start_time.isoformat()} every {interval}"
            )
            return True

    def cancel_event(self, event_id: str) -> bool:
        """
        Cancel a scheduled event.

        Args:
            event_id: ID of event to cancel

        Returns:
            True if event was found and cancelled, False otherwise
        """
        with self._lock:
            if event_id in self._events:
                del self._events[event_id]
                self._logger.info(f"Cancelled event {event_id}")
                return True
            return False

    def cancel_all(self) -> int:
        """
        Cancel all scheduled events.

        Returns:
            Number of events cancelled
        """
        with self._lock:
            count = len(self._events)
            self._events.clear()
            self._logger.info(f"Cancelled all {count} events")
            return count

    def get_scheduled_events(self) -> List[Dict]:
        """
        Get list of all scheduled events.

        Returns:
            List of event dictionaries with their details
        """
        with self._lock:
            return [
                {
                    "id": event_id,
                    "next_trigger": event.get("next_trigger")
                    or event.get("trigger_time"),
                    "recurring": event.get("recurring", False),
                }
                for event_id, event in self._events.items()
            ]

    def _schedule_race_notifications(self, race: Dict) -> None:
        """
        Schedule automatic notifications for a race's sessions.

        Schedules events for:
        - Qualifying start (push notification)
        - Race start (push notification)
        - 1 hour before Race start (betting reminder push notification)

        Args:
            race: Race dictionary with 'id', 'sessions' keys
        """
        from .race_data_manager import race_data_manager

        race_id = race.get("id")
        if not race_id:
            self._logger.warning("Cannot schedule notifications: race has no ID")
            return

        race_name = race.get("name", race_id)
        sessions = race.get("sessions", [])
        now = timezone_utils.utc_now()

        # Schedule for Qualifying
        qualifying = next((s for s in sessions if s.get("type") == "Qualifying"), None)
        if qualifying:
            q_dt = race_data_manager.get_session_datetime(qualifying)
            if q_dt > now:
                event_id = f"qualifying_start_{race_id}"
                self.schedule_event(
                    event_id,
                    q_dt,
                    self._race_notification_callback,
                    {
                        "race_id": race_id,
                        "race_name": race_name,
                        "session_type": "Qualifying",
                        "offset": "start",
                    },
                )
                self._logger.info(f"Scheduled qualifying start for {race_id} at {q_dt.isoformat()}")

        # Schedule for Race
        race_session = next((s for s in sessions if s.get("type") == "Race"), None)
        if race_session:
            race_dt = race_data_manager.get_session_datetime(race_session)
            one_hour_before = race_dt - timedelta(hours=1)

            # Race start notification
            if race_dt > now:
                event_id = f"race_start_{race_id}"
                self.schedule_event(
                    event_id,
                    race_dt,
                    self._race_notification_callback,
                    {
                        "race_id": race_id,
                        "race_name": race_name,
                        "session_type": "Race",
                        "offset": "start",
                    },
                )
                self._logger.info(f"Scheduled race start for {race_id} at {race_dt.isoformat()}")

            # 1 hour before Race (betting reminder)
            if one_hour_before > now:
                event_id = f"race_1h_before_{race_id}"
                self.schedule_event(
                    event_id,
                    one_hour_before,
                    self._race_notification_callback,
                    {
                        "race_id": race_id,
                        "race_name": race_name,
                        "session_type": "Race",
                        "offset": "1h_before",
                    },
                )
                self._logger.info(f"Scheduled betting reminder for {race_id} at {one_hour_before.isoformat()}")

    def schedule_all_race_notifications(self) -> int:
        """
        Schedule notifications for all upcoming races.

        Returns:
            Number of events scheduled
        """
        from .race_data_manager import race_data_manager

        races = race_data_manager.get_all_races()
        count = 0

        for race in races:
            if race.get("canceled"):
                continue
            self._schedule_race_notifications(race)
            count += 1

        if count > 0:
            self._logger.info(f"Scheduled notifications for {count} races")
        return count

    def _default_race_callback(self, event_id: str, data: Dict) -> None:
        """
        Default callback for race notifications (logs only).

        Args:
            event_id: The event identifier
            data: Event data dictionary with race_id, session_type, etc.
        """
        self._logger.info(f"Race event triggered: {event_id} - {data}")

    def _race_notification_callback(self, event_id: str, data: Dict) -> None:
        """
        Callback for race notifications that sends push notifications to all users.
        
        Args:
            event_id: The event identifier
            data: Event data dictionary with race_id, race_name, session_type, offset
        """
        from .push_manager import push_manager

        race_name = data.get("race_name", data.get("race_id", "Unknown"))
        session_type = data.get("session_type", "Session")
        offset = data.get("offset", "")

        # Determine title and body based on event type
        if offset == "start":
            if session_type == "Qualifying":
                title = f"🏁 {session_type} Starting Now"
                body = f"{race_name} {session_type} is starting."
            else:  # Race
                title = f"🏁 {session_type} Starting Now"
                body = f"{race_name} race is starting NOW!"
        elif offset == "1h_before":
            title = f"⏰ Last Chance to Bet - {race_name}"
            body = f"Race starts in 1 hour. Place your bets now before it's too late!"
        else:
            title = f"F1 Notification: {race_name}"
            body = f"{session_type} event for {race_name}"

        # Send to all subscribed users
        success = push_manager.send_notification_to_all(title, body)
        if success:
            self._logger.info(f"Sent push notification: {title}")
        else:
            self._logger.warning(f"Failed to send push notification: {title}")

    def _get_due_events(self) -> List[tuple]:
        """Get all events that are due to trigger."""
        now = timezone_utils.utc_now()
        due_events = []

        with self._lock:
            for event_id, event in list(self._events.items()):
                trigger_time = event.get("next_trigger") or event.get("trigger_time")
                if trigger_time and trigger_time <= now:
                    due_events.append((event_id, event.copy()))

        return due_events

    def _trigger_event(self, event_id: str, event_data: Dict):
        """Trigger an event's callback."""
        try:
            callback = event_data["callback"]
            callback(event_id, event_data.get("data", {}))
            self._logger.info(f"Triggered event {event_id}")
        except Exception as e:
            self._logger.error(f"Error triggering event {event_id}: {e}")

    def _reschedule_recurring(self, event_id: str, event_data: Dict):
        """Reschedule a recurring event for next trigger."""
        with self._lock:
            if event_id in self._events:
                next_time = event_data["next_trigger"] + event_data["interval"]
                self._events[event_id]["next_trigger"] = next_time
                self._logger.debug(
                    f"Rescheduled recurring event {event_id} to {next_time.isoformat()}"
                )

    def _check_events(self):
        """Check for and trigger due events."""
        due_events = self._get_due_events()
        for event_id, event_data in due_events:
            self._trigger_event(event_id, event_data)

            if event_data.get("recurring"):
                self._reschedule_recurring(event_id, event_data)
            else:
                with self._lock:
                    self._events.pop(event_id, None)

    def _run(self):
        """Main event loop."""
        self._logger.info(
            f"Event manager started, checking every {self.check_interval}s"
        )
        while self._running:
            try:
                self._check_events()
            except Exception as e:
                self._logger.error(f"Event manager error: {e}")
            time.sleep(self.check_interval)

    def start(self):
        """Start the event manager thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the event manager."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        self._logger.info("Event manager stopped")


# Singleton instance
event_manager = EventManager()
