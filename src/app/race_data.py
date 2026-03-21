import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pytz
import requests

class RaceDataManager:
    """Simple race data manager for F1 sessions"""
    
    def __init__(self, data_file: str = None):
        self.data_file = data_file or os.path.join(os.path.dirname(__file__), "data", "races.json")
        self.ensure_data_file_exists()
        # Set default timezone to UTC for race data
        self.utc_timezone = pytz.UTC
        try:
            # Try to get user's local timezone from environment or system
            import tzlocal
            self.local_timezone = tzlocal.get_localzone()
        except (ImportError, Exception):
            # Fallback to UTC if tzlocal not available or other errors
            self.local_timezone = pytz.timezone('UTC')

    def _get_race_datetime(self, race: Dict) -> Optional[datetime]:
        """Helper method to get datetime for a race"""
        try:
            if 'time' in race:
                # Handle timezone format (e.g., "04:00:00Z") by stripping the timezone
                time_str = race['time']
                if 'Z' in time_str:
                    time_str = time_str.replace('Z', '')
                if ':' in time_str and len(time_str.split(':')[0]) == 2:
                    # Already in HH:MM format
                    time_part = time_str[:5]  # Take first 5 chars (HH:MM)
                else:
                    # Handle other formats
                    time_part = time_str[:5] if len(time_str) >= 5 else time_str
                return datetime.strptime(f"{race['date']} {time_part}", "%Y-%m-%d %H:%M")
            elif race.get('sessions') and len(race['sessions']) > 0:
                first_session = race['sessions'][0]
                session_time = first_session.get('time', '00:00')
                # Handle timezone format
                if 'Z' in session_time:
                    session_time = session_time.replace('Z', '')
                if ':' in session_time and len(session_time.split(':')[0]) == 2:
                    time_part = session_time[:5]
                else:
                    time_part = session_time[:5] if len(session_time) >= 5 else session_time
                return datetime.strptime(f"{first_session['date']} {time_part}", "%Y-%m-%d %H:%M")
            elif 'date' in race:
                # Fallback to race date with default time for races without sessions
                return datetime.strptime(f"{race['date']} 00:00", "%Y-%m-%d %H:%M")
        except (ValueError, KeyError):
            return None
        return None
    
    def ensure_data_file_exists(self):
        """Ensure the races.json file exists with default data"""
        if not os.path.exists(self.data_file):
            # Try to fetch data from API first
            try:
                api_data = self.fetch_f1_api_data()
                if api_data:
                    transformed_data = self.transform_api_data(api_data)
                    self.save_races(transformed_data)
                    return
            except Exception as e:
                print(f"Could not fetch from API, using default data: {e}")
            
            # Fallback to default data if API fails
            default_data = {
                "races": [
                    {
                        "id": "bahrain_2024",
                        "name": "Bahrain Grand Prix",
                        "country": "Bahrain",
                        "circuit": "Bahrain International Circuit",
                        "date": "2024-03-02",
                        "time": "15:00:00",
                        "sessions": [
                            {"type": "FP1", "date": "2024-02-29", "time": "11:30:00"},
                            {"type": "FP2", "date": "2024-02-29", "time": "15:00:00"},
                            {"type": "FP3", "date": "2024-03-01", "time": "11:30:00"},
                            {"type": "Qualifying", "date": "2024-03-01", "time": "15:00:00"},
                            {"type": "Race", "date": "2024-03-02", "time": "15:00:00"}
                        ]
                    },
                    {
                        "id": "saudi_arabia_2024",
                        "name": "Saudi Arabian Grand Prix",
                        "country": "Saudi Arabia",
                        "circuit": "Jeddah Corniche Circuit",
                        "date": "2024-03-09",
                        "time": "17:00:00",
                        "sessions": [
                            {"type": "FP1", "date": "2024-03-07", "time": "13:30:00"},
                            {"type": "FP2", "date": "2024-03-07", "time": "17:00:00"},
                            {"type": "FP3", "date": "2024-03-08", "time": "13:30:00"},
                            {"type": "Qualifying", "date": "2024-03-08", "time": "17:00:00"},
                            {"type": "Race", "date": "2024-03-09", "time": "17:00:00"}
                        ]
                    }
                ]
            }
            self.save_races(default_data)
    
    def load_races(self) -> Dict:
        """Load races from JSON file"""
        try:
            with open(self.data_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading races: {e}")
            return {"races": []}
    
    def save_races(self, data: Dict):
        """Save races to JSON file"""
        try:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving races: {e}")
            raise
    
    def get_next_race(self) -> Optional[Dict]:
        """Get the next upcoming race"""
        races = self.load_races().get("races", [])
        now = datetime.now()
        
        upcoming_races = []
        for race in races:
            # Skip canceled races
            if race.get('canceled'):
                continue
            
            race_datetime = self._get_race_datetime(race)
            if race_datetime and race_datetime > now:
                upcoming_races.append(race)
        
        # Return the soonest upcoming race
        if upcoming_races:
            return min(upcoming_races, key=lambda race: self._get_race_datetime(race) or datetime.max)
        
        return None
    
    def get_next_session(self) -> Optional[Dict]:
        """Get the next upcoming session across all races"""
        races = self.load_races().get("races", [])
        now = datetime.now()
        
        all_sessions = []
        for race in races:
            # Skip canceled races
            if race.get('canceled'):
                continue
                
            for session in race.get("sessions", []):
                # Handle 'time' field
                session_time = session.get('time', '00:00:00')
                # Skip sessions with None time
                if session_time is None:
                    continue
                # Handle timezone format (e.g., "04:00:00Z")
                if 'Z' in session_time:
                    session_time = session_time.replace('Z', '')
                if ':' in session_time and len(session_time.split(':')[0]) == 2:
                    time_part = session_time[:5]  # Take first 5 chars (HH:MM)
                else:
                    time_part = session_time[:5] if len(session_time) >= 5 else session_time
                session_datetime = datetime.strptime(f"{session['date']} {time_part}", "%Y-%m-%d %H:%M")
                if session_datetime > now:
                    session_with_race_info = session.copy()
                    session_with_race_info["race_name"] = race["name"]
                    session_with_race_info["race_id"] = race.get("id", "unknown")
                    session_with_race_info["country"] = race.get("country", "Unknown")
                    session_with_race_info["circuit"] = race.get("circuit", "Unknown Circuit")
                    all_sessions.append(session_with_race_info)
        
        # Return the soonest upcoming session
        if all_sessions:
            return min(all_sessions, key=lambda x: self._get_session_datetime(x))
    
    def _get_session_datetime(self, session: Dict) -> datetime:
        """Helper method to get datetime for a session"""
        try:
            session_time = session.get('time', '00:00:00')
            # Skip sessions with None time
            if session_time is None:
                return datetime.max
            # Handle timezone format (e.g., "04:00:00Z")
            if 'Z' in session_time:
                session_time = session_time.replace('Z', '')
            if ':' in session_time and len(session_time.split(':')[0]) == 2:
                time_part = session_time[:5]  # Take first 5 chars (HH:MM)
            else:
                time_part = session_time[:5] if len(session_time) >= 5 else session_time
            return datetime.strptime(f"{session['date']} {time_part}", "%Y-%m-%d %H:%M")
        except (ValueError, KeyError):
            return datetime.max
        
        return None
    
    def get_race_by_id(self, race_id: str) -> Optional[Dict]:
        """Get race by ID"""
        races = self.load_races().get("races", [])
        for race in races:
            if race["id"] == race_id:
                return race
        return None
    
    def add_race(self, race_data: Dict):
        """Add a new race"""
        data = self.load_races()
        data["races"].append(race_data)
        self.save_races(data)
    
    def update_race(self, race_id: str, updated_data: Dict):
        """Update an existing race"""
        data = self.load_races()
        for i, race in enumerate(data["races"]):
            if race["id"] == race_id:
                data["races"][i] = updated_data
                self.save_races(data)
                return True
        return False
    
    def delete_race(self, race_id: str) -> bool:
        """Delete a race"""
        data = self.load_races()
        original_length = len(data["races"])
        data["races"] = [race for race in data["races"] if race["id"] != race_id]
        
        if len(data["races"]) < original_length:
            self.save_races(data)
            return True
        return False
    
    def get_upcoming_races(self, limit: int = 5) -> List[Dict]:
        """Get upcoming races"""
        races = self.load_races().get("races", [])
        now = datetime.now()
        
        upcoming = []
        for race in races:
            race_datetime = self._get_race_datetime(race)
            if race_datetime and race_datetime > now:
                upcoming.append(race)
        
        # Sort by date and limit
        upcoming.sort(key=lambda race: self._get_race_datetime(race) or datetime.min)
        return upcoming[:limit]
    
    def get_all_races(self) -> List[Dict]:
        """Get all races"""
        return self.load_races().get("races", [])

    def convert_utc_to_local(self, date_str: str, time_str: str, timezone_str: str = "UTC") -> Dict:
        """Convert UTC time to local time"""
        try:
            # Parse the UTC datetime
            utc_time = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            utc_time = self.utc_timezone.localize(utc_time)
            
            # Convert to local timezone
            local_time = utc_time.astimezone(self.local_timezone)
            
            return {
                "utc": f"{date_str} {time_str} UTC",
                "local": local_time.strftime("%Y-%m-%d %H:%M"),
                "timezone": str(self.local_timezone),
                "formatted_local": local_time.strftime("%a, %d %b %Y %H:%M"),
                "time_only": local_time.strftime("%H:%M"),
                "iso_format": local_time.isoformat()
            }
        except Exception as e:
            return {
                "utc": f"{date_str} {time_str} UTC",
                "local": f"{date_str} {time_str} (UTC)",
                "timezone": "UTC",
                "formatted_local": f"{date_str} {time_str}",
                "time_only": time_str,
                "iso_format": f"{date_str}T{time_str}:00Z"
            }

    def add_timezone_info_to_race(self, race: Dict) -> Dict:
        """Add timezone-converted times to a race"""
        race = race.copy()
        
        # Convert race time
        if 'date' in race and 'time' in race:
            race_time = race.get('time', '00:00')
            race['time_info'] = self.convert_utc_to_local(race['date'], race_time)
        
        # Convert session times
        if 'sessions' in race:
            for session in race['sessions']:
                if 'date' in session and 'time' in session:
                    session_time = session.get('time', '00:00')
                    session['time_info'] = self.convert_utc_to_local(session['date'], session_time)
        
        return race

    def add_timezone_info_to_races(self, races: List[Dict]) -> List[Dict]:
        """Add timezone info to all races"""
        return [self.add_timezone_info_to_race(race) for race in races]

    def get_races_with_timezone_info(self) -> List[Dict]:
        """Get all races with timezone-converted times"""
        races = self.get_all_races()
        return self.add_timezone_info_to_races(races)

    def fetch_f1_api_data(self) -> Optional[Dict]:
        """Fetch data from F1 API"""
        try:
            response = requests.get("https://f1api.dev/api/current", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching F1 API data: {e}")
            return None

    def transform_api_data(self, api_data: Dict) -> Dict:
        """Transform F1 API data to our internal format"""
        races = []
        
        for api_race in api_data.get("races", []):
            # Extract schedule data
            schedule = api_race.get("schedule", {})
            
            # Build sessions list
            sessions = []
            
            # Add FP1 if available
            if schedule.get("fp1"):
                sessions.append({
                    "type": "FP1",
                    "date": schedule["fp1"]["date"],
                    "time": schedule["fp1"]["time"]
                })
            
            # Add FP2 if available
            if schedule.get("fp2"):
                sessions.append({
                    "type": "FP2",
                    "date": schedule["fp2"]["date"],
                    "time": schedule["fp2"]["time"]
                })
            
            # Add FP3 if available
            if schedule.get("fp3"):
                sessions.append({
                    "type": "FP3",
                    "date": schedule["fp3"]["date"],
                    "time": schedule["fp3"]["time"]
                })
            
            # Add Sprint Qualifying if available and has valid data
            if schedule.get("sprintQualy") and schedule["sprintQualy"]["date"] and schedule["sprintQualy"]["time"]:
                sessions.append({
                    "type": "Sprint Qualifying",
                    "date": schedule["sprintQualy"]["date"],
                    "time": schedule["sprintQualy"]["time"]
                })
            
            # Add Qualifying
            if schedule.get("qualy"):
                sessions.append({
                    "type": "Qualifying",
                    "date": schedule["qualy"]["date"],
                    "time": schedule["qualy"]["time"]
                })
            
            # Add Sprint Race if available and has valid data
            if schedule.get("sprintRace") and schedule["sprintRace"]["date"] and schedule["sprintRace"]["time"]:
                sessions.append({
                    "type": "Sprint Race",
                    "date": schedule["sprintRace"]["date"],
                    "time": schedule["sprintRace"]["time"]
                })
            
            # Add Race
            if schedule.get("race"):
                sessions.append({
                    "type": "Race",
                    "date": schedule["race"]["date"],
                    "time": schedule["race"]["time"]
                })
            
            # Build race object
            race = {
                "id": api_race["raceId"],
                "name": api_race["raceName"],
                "country": api_race["circuit"]["country"],
                "circuit": api_race["circuit"]["circuitName"],
                "date": schedule["race"]["date"],
                "time": schedule["race"]["time"],
                "sessions": sessions,
                "round": api_race.get("round"),
                "laps": api_race.get("laps"),
                "circuit_length": api_race["circuit"].get("circuitLength"),
                "city": api_race["circuit"].get("city"),
                "fast_lap": api_race.get("fast_lap", {}).get("fast_lap"),
                "fast_lap_driver": api_race.get("fast_lap", {}).get("fast_lap_driver_id"),
                "winner": api_race.get("winner"),
                "team_winner": api_race.get("teamWinner")
            }
            
            races.append(race)
        
        return {"races": races}

    def update_races_from_api(self) -> bool:
        """Update races from F1 API"""
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

# Global instance for easy access
race_data_manager = RaceDataManager()