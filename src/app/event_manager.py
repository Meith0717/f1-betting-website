"""
Event scheduler — one-time timed events on a background thread.

Schedules race notifications (qualifying start, race start, 1h-before-race)
and fires them at the right time. Message content lives in NotificationService.
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Callable, Dict, Optional

from .core.logger import get_event_logger
from .timezone_utils import timezone_utils

logger = get_event_logger()


class EventManager:
    """Schedules and triggers one-time events on a background thread."""

    def __init__(self, check_interval: int = 10):
        self.check_interval = check_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._events: Dict[str, Dict] = {}
        self._lock = threading.Lock()

    def list_events(self) -> list:
        """Snapshot of pending events as dicts, sorted by trigger time."""
        with self._lock:
            items = sorted(self._events.items(), key=lambda kv: kv[1]["trigger_time"])
        return [
            {
                "id": event_id,
                "trigger_time": ev["trigger_time"].isoformat(),
                "data": ev.get("data", {}),
            }
            for event_id, ev in items
        ]

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
                logger.warning("Event %s already exists", event_id)
                return False
            self._events[event_id] = {
                "trigger_time": trigger_time,
                "callback": callback,
                "data": data or {},
            }
        logger.info("Scheduled %s at %s", event_id, trigger_time.isoformat())
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
            # Resolve attempt a few hours after the race (results are published by then)
            resolve_at = race_data_manager.get_session_datetime(race_session) + timedelta(hours=3)
            if resolve_at > now:
                self.schedule_event(
                    f"resolve_attempt_{race_id}", resolve_at, self._resolve_attempt, {"race_id": race_id}
                )

    # -- Recurring maintenance job (daily at 00:00 and 12:00 server time) ---

    @staticmethod
    def _localize(tz, naive: datetime) -> datetime:
        if hasattr(tz, "localize"):  # pytz
            return tz.localize(naive)
        return naive.replace(tzinfo=tz)  # zoneinfo

    def next_maintenance_run(self) -> datetime:
        """Next 00:00 or 12:00 in the server's local timezone, as UTC-aware."""
        tz = timezone_utils.local_timezone
        naive = timezone_utils.utc_now().astimezone(tz).replace(tzinfo=None)
        for hour in (0, 12):
            candidate = naive.replace(hour=hour, minute=0, second=0, microsecond=0)
            if candidate > naive:
                return self._localize(tz, candidate).astimezone(timezone_utils.utc_timezone)
        next_day = (naive + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return self._localize(tz, next_day).astimezone(timezone_utils.utc_timezone)

    def run_maintenance_job(self) -> None:
        """Housekeeping: notification events for today's sessions, then resolve
        closed-but-unresolved races via the F1 API and announce results."""
        from .race_data_manager import race_data_manager
        from .services import bet_service
        from .services.resolution_service import resolution_service
        from .services.notification_service import notification_service

        logger.info("Running maintenance job")
        now = timezone_utils.utc_now()
        window_end = now + timedelta(hours=24)

        # 1. Notification events for races with a session in the next 24h,
        #    plus a race-weekend overview when FP1 is in that window
        for race in race_data_manager.get_all_races():
            if race.get("canceled"):
                continue
            upcoming = [
                s for s in race.get("sessions", [])
                if now < race_data_manager.get_session_datetime(s) <= window_end
            ]
            if upcoming:
                self.schedule_race_notifications(race)
                fp1 = next((s for s in upcoming if s.get("type") == "FP1"), None)
                if fp1:
                    self._schedule_weekend_overview(race, fp1)

        # 2. Close started races, then schedule an API resolve attempt for
        #    each closed-but-unresolved race
        bet_service.check_and_close_expired()
        data = bet_service.load_all()
        changed = False
        for race_id, entry in data.get("race_bets", {}).items():
            if entry.get("status") == "closed":
                self.schedule_resolve_attempt(race_id)
            # 3. Announce results once per race
            if entry.get("status") == "resolved" and not entry.get("results_notification_sent"):
                race = race_data_manager.get_race_by_id(race_id)
                notification_service.send_race_notification(
                    {
                        "race_id": race_id,
                        "race_name": race.get("name", race_id) if race else race_id,
                        "session_type": "Results",
                        "offset": "results_ready",
                    }
                )
                entry["results_notification_sent"] = True
                changed = True
        if changed:
            bet_service.save_all(data)

    def _schedule_weekend_overview(self, race: Dict, fp1_session: Dict) -> None:
        """Schedule a race-weekend overview notification at 09:00 server-local
        on the FP1 day (or shortly after, if that time has already passed)."""
        from .race_data_manager import race_data_manager
        from .services.notification_service import notification_service

        now = timezone_utils.utc_now()
        tz = timezone_utils.local_timezone
        fp1_local = race_data_manager.get_session_datetime(fp1_session).astimezone(tz)
        trigger = self._localize(
            tz, fp1_local.replace(tzinfo=None).replace(hour=9, minute=0, second=0, microsecond=0)
        ).astimezone(timezone_utils.utc_timezone)
        if trigger <= now:
            trigger = now + timedelta(minutes=5)

        lines = []
        for s in sorted(race.get("sessions", []), key=race_data_manager.get_session_datetime):
            dt = race_data_manager.get_session_datetime(s)
            if dt > now:
                local = dt.astimezone(timezone_utils.local_timezone)
                lines.append(f"{s.get('type')} {local.strftime('%a %H:%M')}")

        self.schedule_event(
            f"weekend_overview_{race.get('id')}",
            trigger,
            lambda eid, d: notification_service.send_race_notification(d),
            {
                "race_id": race.get("id"),
                "race_name": race.get("name", race.get("id", "")),
                "session_type": "Weekend",
                "offset": "weekend_overview",
                "schedule": " · ".join(lines),
            },
        )

    def schedule_resolve_attempt(self, race_id: str) -> None:
        """Schedule a one-time API resolve attempt: 3h after race start, or soon
        if that moment has already passed. Idempotent via the event id."""
        from .race_data_manager import race_data_manager

        race = race_data_manager.get_race_by_id(race_id)
        now = timezone_utils.utc_now()
        trigger = now + timedelta(minutes=5)
        if race:
            race_dt = race_data_manager.get_race_datetime(race)
            if race_dt:
                candidate = race_dt + timedelta(hours=3)
                if candidate > now:
                    trigger = candidate
        self.schedule_event(
            f"resolve_attempt_{race_id}", trigger, self._resolve_attempt, {"race_id": race_id}
        )

    def _resolve_attempt(self, event_id: str, data: Dict) -> None:
        """Try resolving a closed race via the F1 API; announce results on success."""
        from .race_data_manager import race_data_manager
        from .services import bet_service
        from .services.resolution_service import resolution_service
        from .services.notification_service import notification_service

        race_id = data.get("race_id")
        if not race_id:
            return
        if resolution_service.resolve_from_api(race_id):
            logger.info("Race %s resolved via resolve attempt", race_id)
            race = race_data_manager.get_race_by_id(race_id)
            notification_service.send_race_notification(
                {
                    "race_id": race_id,
                    "race_name": race.get("name", race_id) if race else race_id,
                    "session_type": "Results",
                    "offset": "results_ready",
                }
            )
            bdata = bet_service.load_all()
            entry = bdata.get("race_bets", {}).get(race_id)
            if entry is not None:
                entry["results_notification_sent"] = True
                bet_service.save_all(bdata)

    def _maintenance_tick(self, event_id: str, data: Dict) -> None:
        """Fire the maintenance job and schedule the next 00:00/12:00 run."""
        try:
            self.run_maintenance_job()
        except Exception as e:
            logger.error("Maintenance job failed: %s", e)
        trigger = self.next_maintenance_run()
        self.schedule_event(
            f"maintenance_job_{int(trigger.timestamp())}", trigger, self._maintenance_tick, {}
        )

    def start_maintenance_job(self) -> None:
        """Run the maintenance job immediately, then at 00:00/12:00 server time."""
        self.run_maintenance_job()
        trigger = self.next_maintenance_run()
        self.schedule_event(
            f"maintenance_job_{int(trigger.timestamp())}", trigger, self._maintenance_tick, {}
        )

    # -- Weekly data refresh (Mondays 00:00 server time) --------------------

    def next_weekly_refresh(self) -> datetime:
        """Next Monday 00:00 in the server's local timezone, as UTC-aware."""
        tz = timezone_utils.local_timezone
        naive = timezone_utils.utc_now().astimezone(tz).replace(tzinfo=None)
        days_ahead = (0 - naive.weekday()) % 7  # Monday == 0
        candidate = (naive + timedelta(days=days_ahead)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        if candidate <= naive:
            candidate = (naive + timedelta(days=7)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        return self._localize(tz, candidate).astimezone(timezone_utils.utc_timezone)

    def run_weekly_refresh(self) -> None:
        """Refresh race schedule and drivers from the F1 API, then reschedule
        notifications so schedule changes take effect without a restart."""
        from .race_data_manager import race_data_manager
        from .services.resolution_service import resolution_service

        logger.info("Running weekly refresh")
        if race_data_manager.update_races_from_api():
            logger.info("Race schedule refreshed from F1 API")
        if race_data_manager.update_drivers_from_api():
            logger.info("Drivers refreshed from F1 API")
            resolution_service.refresh_driver_teams()
        # Notification events are (re)created by the maintenance job's 24h scan

    def _weekly_tick(self, event_id: str, data: Dict) -> None:
        try:
            self.run_weekly_refresh()
        except Exception as e:
            logger.error("Weekly refresh failed: %s", e)
        trigger = self.next_weekly_refresh()
        self.schedule_event(
            f"weekly_refresh_{int(trigger.timestamp())}", trigger, self._weekly_tick, {}
        )

    def start_weekly_refresh(self) -> None:
        """Schedule the weekly refresh (no immediate run — admin can trigger it)."""
        trigger = self.next_weekly_refresh()
        self.schedule_event(
            f"weekly_refresh_{int(trigger.timestamp())}", trigger, self._weekly_tick, {}
        )

    def _check_events(self) -> None:
        """Trigger all due events and remove them."""
        now = timezone_utils.utc_now()
        due = []
        with self._lock:
            for event_id, event in list(self._events.items()):
                if event["trigger_time"] <= now:
                    due.append((event_id, event))

        for event_id, event in due:
            logger.info("Firing %s (trigger %s)", event_id, event["trigger_time"].isoformat())
            try:
                event["callback"](event_id, event["data"])
            except Exception as e:
                logger.error("Error triggering event %s: %s", event_id, e)
            with self._lock:
                self._events.pop(event_id, None)

    def _run(self) -> None:
        logger.info("Event manager started, checking every %ds", self.check_interval)
        while self._running:
            try:
                self._check_events()
            except Exception as e:
                logger.error("Event manager error: %s", e)
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
        logger.info("Event manager stopped")


event_manager = EventManager()
