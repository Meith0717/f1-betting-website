import json
import os
from datetime import datetime
from typing import Dict, List, Optional

import pytz


class RaceDataManager:
    """Simple race data manager for F1 sessions."""

    def __init__(self, data_file: str = None):
        self.data_file = data_file or os.path.join(
            os.path.dirname(__file__), "data", "races.json"
        )
        self.canceled_file = os.path.join(
            os.path.dirname(__file__), "data", "canceled.json"
        )
        self.drivers_file = os.path.join(
            os.path.dirname(__file__), "data", "drivers.json"
        )
        self.utc_timezone = pytz.UTC

        try:
            import tzlocal

            self.local_timezone = tzlocal.get_localzone()
        except (ImportError, Exception):
            self.local_timezone = pytz.UTC

    def _utc_now(self) -> datetime:
        return datetime.now(pytz.UTC)

    def _clean_time_string(self, time_str: Optional[str]) -> str:
        if not time_str:
            return "00:00:00"

        cleaned = str(time_str).strip()
        if cleaned.endswith("Z"):
            cleaned = cleaned[:-1]

        if "." in cleaned:
            cleaned = cleaned.split(".", 1)[0]

        return cleaned

    def _parse_utc_datetime(self, date_str: str, time_str: Optional[str]) -> Optional[datetime]:
        """Parse date/time strings as a UTC-aware datetime."""
        try:
            if not date_str:
                return None

            cleaned_time = self._clean_time_string(time_str)

            if len(cleaned_time.split(":")) >= 3:
                dt = datetime.strptime(f"{date_str} {cleaned_time[:8]}", "%Y-%m-%d %H:%M:%S")
            else:
                dt = datetime.strptime(f"{date_str} {cleaned_time[:5]}", "%Y-%m-%d %H:%M")

            return self.utc_timezone.localize(dt)
        except Exception:
            return None

    def _get_race_datetime(self, race: Dict) -> Optional[datetime]:
        """Helper method to get timezone-aware datetime for a race."""
        try:
            # First try to get race datetime from sessions (new structure)
            if race.get("sessions"):
                # Find the Race session specifically
                race_session = next((s for s in race["sessions"] if s["type"] == "Race"), None)
                if race_session:
                    parsed = self._parse_utc_datetime(
                        race_session.get("date"), race_session.get("time")
                    )
                    if parsed:
                        return parsed
                
                # Fallback to first session if Race session not found
                first_session = race["sessions"][0]
                parsed = self._parse_utc_datetime(
                    first_session.get("date"), first_session.get("time")
                )
                if parsed:
                    return parsed

            # Legacy support for old structure (date and time at top level)
            if race.get("date") and race.get("time"):
                parsed = self._parse_utc_datetime(race["date"], race.get("time"))
                if parsed:
                    return parsed

            if race.get("date"):
                return self._parse_utc_datetime(race["date"], "00:00:00")

        except (ValueError, KeyError):
            return None

        return None

    def _get_session_datetime(self, session: Dict) -> datetime:
        """Helper method to get timezone-aware datetime for a session."""
        try:
            parsed = self._parse_utc_datetime(session.get("date"), session.get("time"))
            if parsed:
                return parsed
            return datetime.max.replace(tzinfo=pytz.UTC)
        except (ValueError, KeyError):
            return datetime.max.replace(tzinfo=pytz.UTC)

    def ensure_data_file_exists(self):
        """Ensure the races.json file exists with default data."""
        if os.path.exists(self.data_file):
            return

        try:
            api_data = self.fetch_f1_api_data()
            if api_data:
                transformed_data = self.transform_api_data(api_data)
                self.save_races(transformed_data)
                return
        except Exception as e:
            print(f"Could not fetch from API, using default data: {e}")

        default_data = {
            "races": [
                {
                    "id": "n/a",
                    "name": "n/a",
                    "country": "n/a",
                    "circuit": "n/a",
                    "date": "2024-01-01",
                    "time": "00:00:00",
                    "sessions": [
                        {
                            "type": "n/a",
                            "date": "2024-01-01",
                            "time": "00:00:00",
                        }
                    ],
                }
            ]
        }
        self.save_races(default_data)

    def load_races(self) -> Dict:
        """Load races from JSON file."""
        try:
            if not os.path.exists(self.data_file):
                self.ensure_data_file_exists()

            with open(self.data_file, "r", encoding="utf-8") as f:
                races_data = json.load(f)

            if "races" not in races_data:
                races_data["races"] = []

            return self._add_canceled_status(races_data)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading races: {e}")
            return {"races": []}

    def _add_canceled_status(self, races_data: Dict) -> Dict:
        """Add canceled status to races based on canceled.json."""
        try:
            canceled_race_ids = []
            if os.path.exists(self.canceled_file):
                with open(self.canceled_file, "r", encoding="utf-8") as f:
                    canceled_data = json.load(f)
                    canceled_race_ids = canceled_data.get("canceled_race_ids", [])

            for race in races_data.get("races", []):
                race["canceled"] = race.get("id") in canceled_race_ids

            return races_data
        except Exception as e:
            print(f"Error loading canceled data: {e}")
            for race in races_data.get("races", []):
                race["canceled"] = False
            return races_data

    def save_races(self, data: Dict):
        """Save races to JSON file."""
        try:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)

            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving races: {e}")
            raise

    def get_next_race(self) -> Optional[Dict]:
        """Get the next upcoming race."""
        races = self.load_races().get("races", [])
        now = self._utc_now()

        upcoming_races = []
        for race in races:
            if race.get("canceled"):
                continue

            race_datetime = self._get_race_datetime(race)
            if race_datetime and race_datetime > now:
                upcoming_races.append(race)

        if upcoming_races:
            return min(
                upcoming_races,
                key=lambda race: self._get_race_datetime(race)
                or datetime.max.replace(tzinfo=pytz.UTC),
            )

        return None

    def get_next_session(self) -> Optional[Dict]:
        """Get the next upcoming session across all races."""
        races = self.load_races().get("races", [])
        now = self._utc_now()

        all_sessions = []
        for race in races:
            if race.get("canceled"):
                continue

            for session in race.get("sessions", []):
                if session.get("date") is None:
                    continue

                session_datetime = self._get_session_datetime(session)
                if session_datetime > now:
                    session_with_race_info = session.copy()
                    session_with_race_info["race_name"] = race.get("name")
                    session_with_race_info["race_id"] = race.get("id", "unknown")
                    session_with_race_info["country"] = race.get("country", "Unknown")
                    session_with_race_info["circuit"] = race.get(
                        "circuit", "Unknown Circuit"
                    )
                    all_sessions.append(session_with_race_info)

        if all_sessions:
            return min(all_sessions, key=lambda x: self._get_session_datetime(x))
        return None

    def get_race_by_id(self, race_id: str) -> Optional[Dict]:
        """Get race by ID."""
        races = self.load_races().get("races", [])
        for race in races:
            if race.get("id") == race_id:
                return race
        return None

    def add_race(self, race_data: Dict):
        """Add a new race."""
        data = self.load_races()
        data.setdefault("races", [])
        data["races"].append(race_data)
        self.save_races(data)

    def update_race(self, race_id: str, updated_data: Dict):
        """Update an existing race."""
        data = self.load_races()
        for i, race in enumerate(data.get("races", [])):
            if race.get("id") == race_id:
                data["races"][i] = updated_data
                self.save_races(data)
                return True
        return False

    def delete_race(self, race_id: str) -> bool:
        """Delete a race."""
        data = self.load_races()
        original_length = len(data.get("races", []))
        data["races"] = [race for race in data.get("races", []) if race.get("id") != race_id]

        if len(data["races"]) < original_length:
            self.save_races(data)
            return True
        return False

    def get_upcoming_races(self, limit: int = 5) -> List[Dict]:
        """Get upcoming races."""
        races = self.load_races().get("races", [])
        now = self._utc_now()

        upcoming = []
        for race in races:
            if race.get("canceled"):
                continue

            race_datetime = self._get_race_datetime(race)
            if race_datetime and race_datetime > now:
                upcoming.append(race)

        upcoming.sort(
            key=lambda race: self._get_race_datetime(race)
            or datetime.max.replace(tzinfo=pytz.UTC)
        )
        return upcoming[:limit]

    def get_all_races(self) -> List[Dict]:
        """Get all races."""
        return self.load_races().get("races", [])

    def convert_utc_to_local(
        self, date_str: str, time_str: str, timezone_str: str = "UTC"
    ) -> Dict:
        """Convert UTC time to local time."""
        try:
            parsed = self._parse_utc_datetime(date_str, time_str)
            if not parsed:
                raise ValueError("Unable to parse datetime")

            local_time = parsed.astimezone(self.local_timezone)

            return {
                "utc": f"{date_str} {self._clean_time_string(time_str)} UTC",
                "local": local_time.strftime("%Y-%m-%d %H:%M"),
                "timezone": str(self.local_timezone),
                "formatted_local": local_time.strftime("%a, %d %b %Y %H:%M"),
                "time_only": local_time.strftime("%H:%M"),
                "iso_format": local_time.isoformat(),
            }
        except Exception:
            cleaned = self._clean_time_string(time_str)
            return {
                "utc": f"{date_str} {cleaned} UTC",
                "local": f"{date_str} {cleaned} (UTC)",
                "timezone": "UTC",
                "formatted_local": f"{date_str} {cleaned}",
                "time_only": cleaned[:5],
                "iso_format": f"{date_str}T{cleaned}:00Z",
            }

    def add_timezone_info_to_race(self, race: Dict) -> Dict:
        """Add timezone-converted times to a race."""
        race = race.copy()

        if "date" in race and "time" in race:
            race["time_info"] = self.convert_utc_to_local(race["date"], race["time"])

        if "sessions" in race:
            for session in race["sessions"]:
                if "date" in session and "time" in session:
                    session["time_info"] = self.convert_utc_to_local(
                        session["date"], session["time"]
                    )

        return race

    def add_timezone_info_to_races(self, races: List[Dict]) -> List[Dict]:
        """Add timezone info to all races."""
        return [self.add_timezone_info_to_race(race) for race in races]

    def add_timezone_info_to_session(self, session: Dict) -> Dict:
        """Add timezone-converted time to a session."""
        session = session.copy()
        if "date" in session and "time" in session:
            session["time_info"] = self.convert_utc_to_local(
                session["date"], session["time"]
            )
        return session

    def get_canceled_race_ids(self) -> List[str]:
        """Get list of canceled race IDs."""
        try:
            if os.path.exists(self.canceled_file):
                with open(self.canceled_file, "r", encoding="utf-8") as f:
                    canceled_data = json.load(f)
                    return canceled_data.get("canceled_race_ids", [])
            return []
        except Exception as e:
            print(f"Error loading canceled race IDs: {e}")
            return []

    def set_canceled_race_ids(self, race_ids: List[str]) -> bool:
        """Update the list of canceled race IDs."""
        try:
            canceled_data = {
                "canceled_race_ids": race_ids,
                "notes": "Add race IDs to this list to mark them as canceled. Race IDs should match the id field from races.json",
            }
            os.makedirs(os.path.dirname(self.canceled_file), exist_ok=True)
            with open(self.canceled_file, "w", encoding="utf-8") as f:
                json.dump(canceled_data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving canceled race IDs: {e}")
            return False

    def cancel_race(self, race_id: str) -> bool:
        """Mark a race as canceled."""
        if not race_id:
            return False

        canceled_ids = self.get_canceled_race_ids()
        if race_id not in canceled_ids:
            canceled_ids.append(race_id)
            return self.set_canceled_race_ids(canceled_ids)
        return True

    def uncancel_race(self, race_id: str) -> bool:
        """Remove canceled status from a race."""
        if not race_id:
            return False

        canceled_ids = self.get_canceled_race_ids()
        if race_id in canceled_ids:
            canceled_ids.remove(race_id)
            return self.set_canceled_race_ids(canceled_ids)
        return True

    def fetch_f1_api_data(self) -> Optional[Dict]:
        """Fetch data from F1 API."""
        try:
            import requests

            response = requests.get("https://f1api.dev/api/current", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching F1 API data: {e}")
            return None

    def transform_api_data(self, api_data: Dict) -> Dict:
        """Transform F1 API data to our internal format."""
        races = []

        for api_race in api_data.get("races", []):
            schedule = api_race.get("schedule", {})
            sessions = []

            def _append_session(session_type: str, key: str):
                session_data = schedule.get(key)
                if session_data and session_data.get("date") and session_data.get("time"):
                    sessions.append(
                        {
                            "type": session_type,
                            "date": session_data["date"],
                            "time": session_data["time"],
                        }
                    )

            _append_session("FP1", "fp1")
            _append_session("FP2", "fp2")
            _append_session("FP3", "fp3")

            if schedule.get("sprintQualy") and schedule["sprintQualy"].get("date") and schedule["sprintQualy"].get("time"):
                sessions.append(
                    {
                        "type": "Sprint Qualifying",
                        "date": schedule["sprintQualy"]["date"],
                        "time": schedule["sprintQualy"]["time"],
                    }
                )

            _append_session("Qualifying", "qualy")

            if schedule.get("sprintRace") and schedule["sprintRace"].get("date") and schedule["sprintRace"].get("time"):
                sessions.append(
                    {
                        "type": "Sprint Race",
                        "date": schedule["sprintRace"]["date"],
                        "time": schedule["sprintRace"]["time"],
                    }
                )

            if not schedule.get("race") or not schedule["race"].get("date") or not schedule["race"].get("time"):
                continue

            # Add race as a session for consistency
            sessions.append(
                {
                    "type": "Race",
                    "date": schedule["race"]["date"],
                    "time": schedule["race"]["time"],
                }
            )

            race = {
                "id": api_race.get("raceId"),
                "name": api_race.get("raceName"),
                "country": api_race.get("circuit", {}).get("country", "Unknown"),
                "circuit": api_race.get("circuit", {}).get("circuitName", "Unknown"),
                "sessions": sessions,
                "round": api_race.get("round"),
                "city": api_race.get("circuit", {}).get("city"),
            }

            races.append(race)

        return {"races": races}

    def update_races_from_api(self) -> bool:
        """Update races from F1 API."""
        try:
            api_data = self.fetch_f1_api_data()
            if api_data:
                transformed_data = self.transform_api_data(api_data)
                self.save_races(transformed_data)
                return True
            return False
        except Exception as e:
            print(f"Error updating races from API: {e}")
            return False

    def fetch_drivers_api_data(self) -> Optional[Dict]:
        """Fetch drivers data from F1 API."""
        try:
            import requests

            response = requests.get(
                "https://f1api.dev/api/current/drivers", timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching drivers from API: {e}")
            return None

    def save_drivers(self, data: Dict) -> bool:
        """Save drivers to JSON file."""
        try:
            os.makedirs(os.path.dirname(self.drivers_file), exist_ok=True)
            with open(self.drivers_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving drivers: {e}")
            return False

    def load_drivers(self) -> Dict:
        """Load drivers from JSON file."""
        try:
            if not os.path.exists(self.drivers_file):
                return {"drivers": []}
            with open(self.drivers_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading drivers: {e}")
            return {"drivers": []}

    def get_all_drivers(self) -> List[Dict]:
        """Get all drivers."""
        drivers_data = self.load_drivers()
        return drivers_data.get("drivers", [])

    def update_drivers_from_api(self) -> bool:
        """Update drivers from F1 API."""
        try:
            api_data = self.fetch_drivers_api_data()
            if api_data:
                self.save_drivers(api_data)
                return True
            return False
        except Exception as e:
            print(f"Error updating drivers from API: {e}")
            return False


race_data_manager = RaceDataManager()