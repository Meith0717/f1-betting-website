"""
Bet lifecycle service: placement, retrieval, closure, and eligibility checks.

Extracted from the monolithic BettingManager. Handles only the bet data
itself — scoring lives in core/scoring.py, resolution in resolution_service.py.
"""

import os
from datetime import timedelta
from typing import Dict, List, Optional

from ..core import JsonStore
from ..core.logger import get_logger
from ..timezone_utils import timezone_utils

logger = get_logger(__name__)


class BetService:
    """Manages bet storage and lifecycle."""

    def __init__(self, data_file: str = None, race_manager=None):
        if data_file is None:
            data_file = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "data", "bets.json"
            )
        self._store = JsonStore(
            data_file,
            default={
                "race_bets": {},
                "metadata": {"created_at": timezone_utils.now_iso(), "version": "1.0"},
            },
        )
        self._race_manager = race_manager  # injected to avoid circular import

    def set_race_manager(self, race_manager) -> None:
        """Inject the race manager (called after both are constructed)."""
        self._race_manager = race_manager

    # -- Raw data access ----------------------------------------------------

    def load_all(self) -> Dict:
        """Load the full bets data structure."""
        data = self._store.load()
        data.setdefault("race_bets", {})
        data.setdefault("metadata", {})
        return data

    def save_all(self, data: Dict) -> None:
        self._store.save(data)

    # -- Bet queries --------------------------------------------------------

    def get_user_bets(self, username: str) -> Dict[str, dict]:
        """Get all bets for a user, keyed by race_id."""
        result = {}
        for race_id, race_data in self.load_all()["race_bets"].items():
            user_bets = race_data.get("user_bets", {})
            if username in user_bets:
                result[race_id] = user_bets[username]
        return result

    def get_race_status(self, race_id: str) -> Optional[str]:
        """Get the status of a race's bet pool ('active', 'closed', 'resolved')."""
        data = self.load_all()
        return data["race_bets"].get(race_id, {}).get("status")

    # -- Bet mutation -------------------------------------------------------

    def place_bet(
        self, username: str, race_id: str, drivers: List[str], fastest_lap: str
    ) -> bool:
        """Place (or overwrite) a bet. Validates 3 unique drivers + fastest lap."""
        if len(drivers) != 3 or len(set(drivers)) != 3 or not fastest_lap:
            logger.warning(
                "Invalid bet from %s on %s: drivers=%s, fastest_lap=%s",
                username, race_id, drivers, fastest_lap,
            )
            return False

        data = self.load_all()
        data["race_bets"].setdefault(
            race_id, {"user_bets": {}, "status": "active"}
        )
        data["race_bets"][race_id]["user_bets"][username] = {
            "drivers": drivers,
            "fastest_lap": fastest_lap,
            "created_at": timezone_utils.now_iso(),
        }
        self.save_all(data)
        logger.info(
            "Bet placed: %s on %s - %s (FL: %s)", username, race_id, drivers, fastest_lap
        )
        return True

    def remove_user_bets(self, username: str) -> int:
        """Remove all of a user's bets across every race. Returns count removed."""
        data = self.load_all()
        removed = 0
        for race_id in list(data["race_bets"].keys()):
            entry = data["race_bets"][race_id]
            if username in entry.get("user_bets", {}):
                del entry["user_bets"][username]
                removed += 1
                if not entry["user_bets"] and entry.get("status") == "active":
                    del data["race_bets"][race_id]
        if removed:
            self.save_all(data)
            logger.info("Removed %d bets for deleted user %s", removed, username)
        return removed

    def remove_bet(self, username: str, race_id: str) -> bool:
        """Remove a user's bet from a race. Cleans up empty race entries."""
        data = self.load_all()
        race_entry = data["race_bets"].get(race_id)
        if not race_entry or username not in race_entry.get("user_bets", {}):
            return False

        del race_entry["user_bets"][username]
        if not race_entry["user_bets"]:
            del data["race_bets"][race_id]

        self.save_all(data)
        return True

    # -- Race lifecycle -----------------------------------------------------

    def close_race(self, race_id: str, data: Dict = None) -> bool:
        """Mark a race's bet pool as closed (race has started)."""
        if data is None:
            data = self.load_all()

        entry = data["race_bets"].setdefault(
            race_id,
            {"user_bets": {}, "status": "closed",
             "closed_at": timezone_utils.now_iso()},
        )
        if entry.get("status") == "active":
            entry["status"] = "closed"
            entry["closed_at"] = timezone_utils.now_iso()

        self.save_all(data)
        logger.info("Race %s marked as closed", race_id)
        return True

    def check_and_close_expired(self) -> int:
        """Auto-close bets for all races that have started. Returns count closed."""
        if not self._race_manager:
            return 0

        data = self.load_all()
        now = timezone_utils.utc_now()
        closed = 0

        for race in self._race_manager.get_all_races():
            race_id = race.get("id")
            if not race_id:
                continue
            entry = data["race_bets"].get(race_id, {})
            if entry.get("status") in ("closed", "resolved"):
                continue
            race_dt = self._race_manager._get_race_datetime(race)
            if race_dt and race_dt <= now:
                self.close_race(race_id, data)
                closed += 1

        if closed:
            logger.info("Auto-closed bets for %d started races", closed)
        return closed

    def is_betting_closed(self, race_id: str) -> bool:
        """Check if betting is closed for a race (started or explicitly closed)."""
        status = self.get_race_status(race_id)
        if status in ("closed", "resolved"):
            return True
        if not self._race_manager:
            return True
        race = self._race_manager.get_race_by_id(race_id)
        if not race:
            return True
        race_dt = self._race_manager._get_race_datetime(race)
        if not race_dt:
            return True
        buffer = timedelta(minutes=2)
        return race_dt - buffer <= timezone_utils.utc_now()

    def can_bet_on_race(self, race_id: str, username: str = None) -> bool:
        """
        Full eligibility check: race exists, not canceled, not started,
        not already resolved/closed, and user hasn't already bet.
        Only the very next upcoming race is open for betting.
        """
        if not self._race_manager:
            return False

        race = self._race_manager.get_race_by_id(race_id)
        if not race:
            return False

        canceled = self._race_manager.get_canceled_race_ids()
        if race_id in canceled or race.get("canceled"):
            return False

        race_dt = self._race_manager._get_race_datetime(race)
        if not race_dt or race_dt <= timezone_utils.utc_now():
            return False

        if username and race_id in self.get_user_bets(username):
            return False

        status = self.get_race_status(race_id)
        if status in ("closed", "resolved"):
            return False

        # Only allow betting on the next upcoming race
        now = timezone_utils.utc_now()
        upcoming = []
        for r in self._race_manager.get_all_races():
            r_dt = self._race_manager._get_race_datetime(r)
            if r_dt and r_dt > now and r.get("id") not in canceled:
                upcoming.append((r["id"], r_dt))
        upcoming.sort(key=lambda x: x[1])

        if upcoming and upcoming[0][0] != race_id:
            return False

        return True

    # -- Available drivers --------------------------------------------------

    def get_available_drivers(self) -> List[Dict]:
        """Get formatted driver list for bet forms."""
        if not self._race_manager:
            return []
        drivers = self._race_manager.load_drivers().get("drivers", [])
        return [
            {
                "driver_id": d.get("driverId"),
                "name": f"{d.get('name', '')} {d.get('surname', '')}".strip(),
                "short_name": d.get("shortName", ""),
                "number": d.get("number", "N/A"),
                "team": d.get("teamId", "Unknown"),
            }
            for d in drivers
        ]


# Singleton — race_manager injected after construction to avoid circular imports
bet_service = BetService()
