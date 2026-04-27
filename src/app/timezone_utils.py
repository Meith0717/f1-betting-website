"""
Timezone utilities for F1 Betting Platform.
Handles UTC datetime parsing, conversion, and formatting.
"""

from datetime import datetime
from typing import Dict, List, Optional
import pytz


class TimezoneUtils:
    """Utilities for timezone-aware datetime operations."""

    def __init__(self):
        self.utc_timezone = pytz.UTC

        try:
            import tzlocal
            self.local_timezone = tzlocal.get_localzone()
        except (ImportError, Exception):
            self.local_timezone = pytz.UTC

    def utc_now(self) -> datetime:
        """Get current UTC time as timezone-aware datetime."""
        return datetime.now(pytz.UTC)

    def now_iso(self) -> str:
        """Get current UTC time as ISO string."""
        return self.utc_now().isoformat()

    def clean_time_string(self, time_str: Optional[str]) -> str:
        """
        Clean a time string by removing 'Z' suffix and decimal seconds.
        
        Args:
            time_str: Time string, possibly with 'Z' suffix (e.g., "04:00:00Z")
            
        Returns:
            Cleaned time string (e.g., "04:00:00")
        """
        if not time_str:
            return "00:00:00"

        cleaned = str(time_str).strip()
        if cleaned.endswith("Z"):
            cleaned = cleaned[:-1]

        if "." in cleaned:
            cleaned = cleaned.split(".", 1)[0]

        return cleaned

    def parse_utc_datetime(
        self, date_str: str, time_str: Optional[str]
    ) -> Optional[datetime]:
        """
        Parse date and time strings as a UTC-aware datetime.
        
        Args:
            date_str: Date string in format YYYY-MM-DD
            time_str: Time string (e.g., "04:00:00" or "04:00:00Z")
            
        Returns:
            UTC-aware datetime object, or None if parsing fails
        """
        try:
            if not date_str:
                return None

            cleaned_time = self.clean_time_string(time_str)

            if len(cleaned_time.split(":")) >= 3:
                dt = datetime.strptime(
                    f"{date_str} {cleaned_time[:8]}", "%Y-%m-%d %H:%M:%S"
                )
            else:
                dt = datetime.strptime(
                    f"{date_str} {cleaned_time[:5]}", "%Y-%m-%d %H:%M"
                )

            return self.utc_timezone.localize(dt)
        except Exception:
            return None

    def get_race_datetime(self, race: Dict) -> Optional[datetime]:
        """
        Get timezone-aware datetime for a race from its sessions.
        
        Args:
            race: Race dictionary with 'sessions' key
            
        Returns:
            UTC-aware datetime of the main race session, or None
        """
        try:
            if race.get("sessions"):
                race_session = next(
                    (s for s in race["sessions"] if s["type"] == "Race"), None
                )
                if race_session:
                    parsed = self.parse_utc_datetime(
                        race_session.get("date"), race_session.get("time")
                    )
                    if parsed:
                        return parsed

                first_session = race["sessions"][0]
                parsed = self.parse_utc_datetime(
                    first_session.get("date"), first_session.get("time")
                )
                if parsed:
                    return parsed

            if race.get("date") and race.get("time"):
                parsed = self.parse_utc_datetime(race["date"], race["time"])
                if parsed:
                    return parsed

            if race.get("date"):
                return self.parse_utc_datetime(race["date"], "00:00:00")

        except (ValueError, KeyError):
            pass

        return None

    def get_session_datetime(self, session: Dict) -> datetime:
        """
        Get timezone-aware datetime for a session.
        
        Args:
            session: Session dictionary with 'date' and 'time' keys
            
        Returns:
            UTC-aware datetime, or datetime.max if parsing fails
        """
        try:
            parsed = self.parse_utc_datetime(session.get("date"), session.get("time"))
            if parsed:
                return parsed
        except (ValueError, KeyError):
            pass

        return datetime.max.replace(tzinfo=pytz.UTC)

    def convert_utc_to_local(self, date_str: str, time_str: str) -> Dict:
        """
        Convert UTC datetime to local time with various format options.
        
        Args:
            date_str: Date string in format YYYY-MM-DD
            time_str: Time string (e.g., "04:00:00Z")
            
        Returns:
            Dictionary with multiple time format representations:
            - utc: UTC string representation
            - local: Local time string
            - timezone: Local timezone name
            - formatted_local: Formatted local datetime string
            - time_only: Local time in HH:MM format
            - iso_format: Local ISO format with timezone offset
        """
        try:
            parsed = self.parse_utc_datetime(date_str, time_str)
            if not parsed:
                raise ValueError("Unable to parse datetime")

            local_time = parsed.astimezone(self.local_timezone)

            return {
                "utc": f"{date_str} {self.clean_time_string(time_str)} UTC",
                "local": local_time.strftime("%Y-%m-%d %H:%M"),
                "timezone": str(self.local_timezone),
                "formatted_local": local_time.strftime("%a, %d %b %Y %H:%M"),
                "time_only": local_time.strftime("%H:%M"),
                "iso_format": local_time.isoformat(),
            }
        except Exception:
            cleaned = self.clean_time_string(time_str)
            return {
                "utc": f"{date_str} {cleaned} UTC",
                "local": f"{date_str} {cleaned} (UTC)",
                "timezone": "UTC",
                "formatted_local": f"{date_str} {cleaned}",
                "time_only": cleaned[:5],
                "iso_format": f"{date_str}T{cleaned}:00Z",
            }

    def add_timezone_info_to_race(self, race: Dict) -> Dict:
        """
        Add timezone-converted times to a race dictionary.
        
        Args:
            race: Race dictionary
            
        Returns:
            Race dictionary with added 'time_info' for date/time and sessions
        """
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

    def add_timezone_info_to_session(self, session: Dict) -> Dict:
        """
        Add timezone-converted time to a session dictionary.
        
        Args:
            session: Session dictionary
            
        Returns:
            Session dictionary with added 'time_info'
        """
        session = session.copy()
        if "date" in session and "time" in session:
            session["time_info"] = self.convert_utc_to_local(
                session["date"], session["time"]
            )
        return session

    def add_timezone_info_to_races(self, races: List[Dict]) -> List[Dict]:
        """
        Add timezone info to all races in a list.
        
        Args:
            races: List of race dictionaries
            
        Returns:
            List of race dictionaries with timezone info added
        """
        return [self.add_timezone_info_to_race(race) for race in races]


# Create singleton instance
timezone_utils = TimezoneUtils()
