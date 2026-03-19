import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pytz

class RaceDataManager:
    """Simple race data manager for F1 sessions"""
    
    def __init__(self, data_file: str = None):
        self.data_file = data_file or os.path.join(os.path.dirname(__file__), "data", "races.json")
        self.ensure_data_file_exists()
        # Set default timezone to UTC for race data
        self.utc_timezone = pytz.UTC
        try:
            # Try to get user's local timezone
            self.local_timezone = pytz.timezone('Europe/Paris')  # Default fallback
        except:
            self.local_timezone = pytz.timezone('UTC')
    
    def ensure_data_file_exists(self):
        """Ensure the races.json file exists with default data"""
        if not os.path.exists(self.data_file):
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
            # Use the first session's date/time if race time is not available
            if 'time' in race:
                race_datetime = datetime.strptime(f"{race['date']} {race['time']}", "%Y-%m-%d %H:%M:%S")
            elif race.get('sessions'):
                first_session = race['sessions'][0]
                session_time = first_session.get('time', first_session.get('time', '00:00:00'))
                race_datetime = datetime.strptime(f"{first_session['date']} {session_time}", "%Y-%m-%d %H:%M:%S")
            else:
                continue
            
            if race_datetime > now:
                upcoming_races.append(race)
        
        # Return the soonest upcoming race
        if upcoming_races:
            def get_race_sort_key(race):
                if 'time' in race:
                    return datetime.strptime(f"{race['date']} {race['time']}", "%Y-%m-%d %H:%M:%S")
                elif race.get('sessions'):
                    first_session = race['sessions'][0]
                    session_time = first_session.get('time', first_session.get('time', '00:00:00'))
                    return datetime.strptime(f"{first_session['date']} {session_time}", "%Y-%m-%d %H:%M:%S")
                return datetime.max
            
            return min(upcoming_races, key=get_race_sort_key)
        
        return None
    
    def get_next_session(self) -> Optional[Dict]:
        """Get the next upcoming session across all races"""
        races = self.load_races().get("races", [])
        now = datetime.now()
        
        all_sessions = []
        for race in races:
            for session in race.get("sessions", []):
                # Handle both 'time' and 'time' fields
                session_time = session.get('time', session.get('time', '00:00:00'))
                session_datetime = datetime.strptime(f"{session['date']} {session_time}", "%Y-%m-%d %H:%M:%S")
                if session_datetime > now:
                    session_with_race_info = session.copy()
                    session_with_race_info["race_name"] = race["name"]
                    session_with_race_info["race_id"] = race.get("id", "unknown")
                    session_with_race_info["country"] = race.get("country", "Unknown")
                    session_with_race_info["circuit"] = race.get("circuit", "Unknown Circuit")
                    all_sessions.append(session_with_race_info)
        
        # Return the soonest upcoming session
        if all_sessions:
            return min(all_sessions, key=lambda x: datetime.strptime(
                f"{x['date']} {x.get('time', x.get('time', '00:00:00'))}", 
                "%Y-%m-%d %H:%M:%S"
            ))
        
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
            # Handle both 'time' and missing time fields
            if 'time' in race:
                race_datetime = datetime.strptime(f"{race['date']} {race['time']}", "%Y-%m-%d %H:%M:%S")
            elif race.get('sessions'):
                first_session = race['sessions'][0]
                session_time = first_session.get('time', first_session.get('time', '00:00:00'))
                race_datetime = datetime.strptime(f"{first_session['date']} {session_time}", "%Y-%m-%d %H:%M:%S")
            else:
                continue
            
            if race_datetime > now:
                upcoming.append(race)
        
        # Sort by date and limit
        def get_race_datetime(race):
            if 'time' in race:
                return datetime.strptime(f"{race['date']} {race['time']}", "%Y-%m-%d %H:%M:%S")
            elif race.get('sessions'):
                first_session = race['sessions'][0]
                session_time = first_session.get('time', first_session.get('time', '00:00:00'))
                return datetime.strptime(f"{first_session['date']} {session_time}", "%Y-%m-%d %H:%M:%S")
            return datetime.min
        
        upcoming.sort(key=get_race_datetime)
        return upcoming[:limit]
    
    def get_all_races(self) -> List[Dict]:
        """Get all races"""
        return self.load_races().get("races", [])

    def convert_utc_to_local(self, date_str: str, time_str: str, timezone_str: str = "UTC") -> Dict:
        """Convert UTC time to local time"""
        try:
            # Parse the UTC datetime
            utc_time = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
            utc_time = self.utc_timezone.localize(utc_time)
            
            # Convert to local timezone
            local_time = utc_time.astimezone(self.local_timezone)
            
            return {
                "utc": f"{date_str} {time_str} UTC",
                "local": local_time.strftime("%Y-%m-%d %H:%M:%S"),
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
        if 'date' in race and ('time' in race or 'time' in race):
            race_time = race.get('time', race.get('time', '00:00:00'))
            race['time_info'] = self.convert_utc_to_local(race['date'], race_time)
        
        # Convert session times
        if 'sessions' in race:
            for session in race['sessions']:
                if 'date' in session and ('time' in session or 'time' in session):
                    session_time = session.get('time', session.get('time', '00:00:00'))
                    session['time_info'] = self.convert_utc_to_local(session['date'], session_time)
        
        return race

    def add_timezone_info_to_races(self, races: List[Dict]) -> List[Dict]:
        """Add timezone info to all races"""
        return [self.add_timezone_info_to_race(race) for race in races]

    def get_races_with_timezone_info(self) -> List[Dict]:
        """Get all races with timezone-converted times"""
        races = self.get_all_races()
        return self.add_timezone_info_to_races(races)

# Global instance for easy access
race_data_manager = RaceDataManager()