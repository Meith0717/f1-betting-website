"""
Race data manager — race schedule, drivers, and canceled race tracking.

All persistence goes through JsonStore. Timezone helpers delegate to
TimezoneUtils. F1 API fetching is isolated in the fetch/transform methods.
"""

import os
from datetime import datetime
from typing import Dict, List, Optional

import pytz

from .core import JsonStore
from .core.logger import get_logger
from .timezone_utils import timezone_utils

logger = get_logger(__name__)

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


class RaceDataManager:
    """Manages F1 race, driver, and cancellation data stored in JSON."""

    def __init__(self, data_file: str = None):
        self._races_store = JsonStore(
            data_file or os.path.join(_DATA_DIR, "races.json"),
            default={"races": []},
        )
        self._canceled_store = JsonStore(
            os.path.join(_DATA_DIR, "canceled.json"),
            default={"canceled_race_ids": []},
        )
        self._drivers_store = JsonStore(
            os.path.join(_DATA_DIR, "drivers.json"),
            default={"drivers": []},
        )

    # -- Timezone delegation (backward-compat aliases) ----------------------

    def get_race_datetime(self, race: Dict) -> Optional[datetime]:
        return timezone_utils.get_race_datetime(race)

    def get_session_datetime(self, session: Dict) -> datetime:
        return timezone_utils.get_session_datetime(session)

    _get_race_datetime = get_race_datetime
    _get_session_datetime = get_session_datetime

    def convert_utc_to_local(self, date_str: str, time_str: str, tz: str = "UTC") -> Dict:
        return timezone_utils.convert_utc_to_local(date_str, time_str, tz)

    def add_timezone_info_to_race(self, race: Dict) -> Dict:
        return timezone_utils.add_timezone_info_to_race(race)

    def add_timezone_info_to_session(self, session: Dict) -> Dict:
        return timezone_utils.add_timezone_info_to_session(session)

    def add_timezone_info_to_races(self, races: List[Dict]) -> List[Dict]:
        return timezone_utils.add_timezone_info_to_races(races)

    # -- Races CRUD ---------------------------------------------------------

    def load_races(self) -> Dict:
        """Load races with canceled status merged in."""
        data = self._races_store.load()
        data.setdefault("races", [])
        return self._add_canceled_status(data)

    def save_races(self, data: Dict) -> None:
        self._races_store.save(data)

    def _add_canceled_status(self, races_data: Dict) -> Dict:
        canceled_ids = set(self.get_canceled_race_ids())
        for race in races_data.get("races", []):
            race["canceled"] = race.get("id") in canceled_ids
        return races_data

    def get_all_races(self) -> List[Dict]:
        return self.load_races().get("races", [])

    def get_race_by_id(self, race_id: str) -> Optional[Dict]:
        for race in self.get_all_races():
            if race.get("id") == race_id:
                return race
        return None

    def add_race(self, race_data: Dict) -> None:
        data = self.load_races()
        data.setdefault("races", []).append(race_data)
        self.save_races(data)

    # -- Race queries -------------------------------------------------------

    def _upcoming(self) -> List[Dict]:
        """Non-canceled races with a future race datetime, sorted ascending."""
        now = timezone_utils.utc_now()
        upcoming = []
        for race in self.get_all_races():
            if race.get("canceled"):
                continue
            dt = self.get_race_datetime(race)
            if dt and dt > now:
                upcoming.append(race)
        upcoming.sort(key=lambda r: self.get_race_datetime(r) or datetime.max.replace(tzinfo=pytz.UTC))
        return upcoming

    def get_next_race(self) -> Optional[Dict]:
        upcoming = self._upcoming()
        return upcoming[0] if upcoming else None

    def get_upcoming_races(self, limit: int = 5) -> List[Dict]:
        return self._upcoming()[:limit]

    def get_next_session(self) -> Optional[Dict]:
        now = timezone_utils.utc_now()
        all_sessions = []
        for race in self.get_all_races():
            if race.get("canceled"):
                continue
            for session in race.get("sessions", []):
                if session.get("date") is None:
                    continue
                if self.get_session_datetime(session) > now:
                    s = session.copy()
                    s.update({
                        "race_name": race.get("name"),
                        "race_id": race.get("id", "unknown"),
                        "country": race.get("country", "Unknown"),
                        "circuit": race.get("circuit", "Unknown Circuit"),
                    })
                    all_sessions.append(s)
        if all_sessions:
            return min(all_sessions, key=lambda x: self.get_session_datetime(x))
        return None

    # -- Canceled races -----------------------------------------------------

    def get_canceled_race_ids(self) -> List[str]:
        return self._canceled_store.load().get("canceled_race_ids", [])

    def set_canceled_race_ids(self, race_ids: List[str]) -> bool:
        self._canceled_store.save({"canceled_race_ids": race_ids})
        return True

    def cancel_race(self, race_id: str) -> bool:
        if not race_id:
            return False
        ids = self.get_canceled_race_ids()
        if race_id not in ids:
            ids.append(race_id)
            return self.set_canceled_race_ids(ids)
        return True

    def uncancel_race(self, race_id: str) -> bool:
        if not race_id:
            return False
        ids = self.get_canceled_race_ids()
        if race_id in ids:
            ids.remove(race_id)
            return self.set_canceled_race_ids(ids)
        return True

    # -- Drivers ------------------------------------------------------------

    def load_drivers(self) -> Dict:
        return self._drivers_store.load()

    def save_drivers(self, data: Dict) -> bool:
        self._drivers_store.save(data)
        return True

    def get_all_drivers(self) -> List[Dict]:
        return self.load_drivers().get("drivers", [])

    def get_driver_teams(self) -> Dict[str, str]:
        """driver_id -> team_id."""
        return {
            d["driverId"]: d["teamId"]
            for d in self.get_all_drivers()
            if d.get("driverId") and d.get("teamId")
        }

    def get_driver_short_names(self) -> Dict[str, str]:
        """driver_id -> shortName."""
        return {
            d["driverId"]: d["shortName"]
            for d in self.get_all_drivers()
            if d.get("driverId") and d.get("shortName")
        }

    # -- F1 API (Jolpica / Ergast-compatible, api.jolpi.ca) -------------------

    API_BASE = "https://api.jolpi.ca/ergast/f1"

    # Ergast session key -> our session type label (main race uses top-level date/time)
    _SESSION_MAP = [
        ("FirstPractice", "FP1"),
        ("SecondPractice", "FP2"),
        ("ThirdPractice", "FP3"),
        ("SprintQualifying", "Sprint Qualifying"),
        ("Sprint", "Sprint Race"),
        ("Qualifying", "Qualifying"),
    ]

    def fetch_f1_api_data(self) -> Optional[Dict]:
        try:
            import requests
            resp = requests.get(f"{self.API_BASE}/current.json", timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("Error fetching F1 API data: %s", e)
            return None

    def transform_api_data(self, api_data: Dict) -> Dict:
        """Transform Ergast-format season schedule into our race format.

        Reuses existing race IDs (matched by season+round) so stored bets
        keep pointing at the right race across API updates.
        """
        existing = {
            (r.get("round")): r.get("id")
            for r in self.get_all_races()
        }
        races = []
        for api_race in api_data.get("MRData", {}).get("RaceTable", {}).get("Races", []):
            sessions = []
            for key, label in self._SESSION_MAP:
                sd = api_race.get(key)
                if sd and sd.get("date"):
                    sessions.append({
                        "type": label,
                        "date": sd["date"],
                        "time": sd.get("time", "00:00:00Z"),
                    })

            # Main race datetime comes from the top-level date/time fields
            if not api_race.get("date"):
                continue
            race_session = {
                "type": "Race",
                "date": api_race["date"],
                "time": api_race.get("time", "00:00:00Z"),
            }
            sessions.append(race_session)

            circuit = api_race.get("Circuit", {})
            location = circuit.get("Location", {})
            season = api_race.get("season", "")
            slug = "".join(c if c.isalnum() else "_" for c in api_race.get("raceName", "race").lower())
            slug = "_".join(filter(None, slug.split("_")))
            round_num = int(api_race.get("round", 0))

            races.append({
                "id": existing.get(round_num) or f"{slug}_{season}",
                "name": api_race.get("raceName"),
                "country": location.get("country", "Unknown"),
                "circuit": circuit.get("circuitName", "Unknown"),
                "sessions": sessions,
                "round": int(api_race.get("round", 0)),
                "city": location.get("locality"),
                "date": race_session["date"],
                "time": race_session["time"],
            })

        return {"races": races}

    def update_races_from_api(self) -> bool:
        api_data = self.fetch_f1_api_data()
        if not api_data:
            return False
        self.save_races(self.transform_api_data(api_data))
        return True

    # -- F1 API: drivers ----------------------------------------------------

    def fetch_drivers_api_data(self) -> Optional[Dict]:
        """Fetch drivers + driver standings (for team mapping) and merge them."""
        try:
            import requests
            drivers_resp = requests.get(f"{self.API_BASE}/current/drivers.json", timeout=10)
            drivers_resp.raise_for_status()
            standings_resp = requests.get(f"{self.API_BASE}/current/driverStandings.json", timeout=10)
            standings_resp.raise_for_status()

            drivers = drivers_resp.json().get("MRData", {}).get("DriverTable", {}).get("Drivers", [])
            standings = (
                standings_resp.json()
                .get("MRData", {}).get("StandingsTable", {})
                .get("StandingsLists", [{}])[0]
                .get("DriverStandings", [])
            )
            team_map = {
                s["Driver"]["driverId"]: s["Constructors"][0]["constructorId"]
                for s in standings
                if s.get("Constructors")
            }

            out = []
            for d in drivers:
                out.append({
                    "driverId": d.get("driverId"),
                    "name": d.get("givenName", ""),
                    "surname": d.get("familyName", ""),
                    "shortName": d.get("code", ""),
                    "number": d.get("permanentNumber", "N/A"),
                    "teamId": team_map.get(d.get("driverId"), "Unknown"),
                })
            return {"drivers": out}
        except Exception as e:
            logger.error("Error fetching drivers from API: %s", e)
            return None

    def update_drivers_from_api(self) -> bool:
        api_data = self.fetch_drivers_api_data()
        if not api_data:
            return False
        return self.save_drivers(api_data)


race_data_manager = RaceDataManager()
