from datetime import datetime
from typing import List, Dict, Optional
import json
import os

class F1Circuit:
    """Model for F1 Circuit information"""
    def __init__(self, circuit_id: str, name: str, country: str, city: str, 
                 length_km: float, laps: int, race_distance_km: float, 
                 lap_record: Optional[str] = None, direction: str = "clockwise",
                 first_grand_prix: Optional[int] = None):
        self.circuit_id = circuit_id
        self.name = name
        self.country = country
        self.city = city
        self.length_km = length_km
        self.laps = laps
        self.race_distance_km = race_distance_km
        self.lap_record = lap_record
        self.direction = direction
        self.first_grand_prix = first_grand_prix

    def to_dict(self) -> Dict:
        """Convert circuit to dictionary"""
        return {
            "circuit_id": self.circuit_id,
            "name": self.name,
            "country": self.country,
            "city": self.city,
            "length_km": self.length_km,
            "laps": self.laps,
            "race_distance_km": self.race_distance_km,
            "lap_record": self.lap_record,
            "direction": self.direction,
            "first_grand_prix": self.first_grand_prix
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'F1Circuit':
        """Create circuit from dictionary"""
        return cls(
            circuit_id=data["circuit_id"],
            name=data["name"],
            country=data["country"],
            city=data["city"],
            length_km=data["length_km"],
            laps=data["laps"],
            race_distance_km=data["race_distance_km"],
            lap_record=data.get("lap_record"),
            direction=data.get("direction", "clockwise"),
            first_grand_prix=data.get("first_grand_prix")
        )

class F1Session:
    """Model for F1 Session (FP1, FP2, FP3, Qualifying, Race)"""
    def __init__(self, session_type: str, date: str, time: str, 
                 weather_forecast: Optional[str] = None, completed: bool = False):
        self.session_type = session_type  # FP1, FP2, FP3, Qualifying, Race, Sprint
        self.date = date
        self.time = time
        self.weather_forecast = weather_forecast
        self.completed = completed

    def to_dict(self) -> Dict:
        """Convert session to dictionary"""
        return {
            "session_type": self.session_type,
            "date": self.date,
            "time": self.time,
            "weather_forecast": self.weather_forecast,
            "completed": self.completed
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'F1Session':
        """Create session from dictionary"""
        return cls(
            session_type=data["session_type"],
            date=data["date"],
            time=data["time"],
            weather_forecast=data.get("weather_forecast"),
            completed=data.get("completed", False)
        )

class F1GrandPrix:
    """Model for F1 Grand Prix Weekend"""
    def __init__(self, grand_prix_id: str, year: int, round_number: int,
                 country: str, circuit: F1Circuit, sessions: List[F1Session],
                 is_sprint_weekend: bool = False, official_name: Optional[str] = None):
        self.grand_prix_id = grand_prix_id
        self.year = year
        self.round_number = round_number
        self.country = country
        self.circuit = circuit
        self.sessions = sessions
        self.is_sprint_weekend = is_sprint_weekend
        self.official_name = official_name or f"{country} Grand Prix"

    def get_session_by_type(self, session_type: str) -> Optional[F1Session]:
        """Get session by type (FP1, FP2, etc.)"""
        for session in self.sessions:
            if session.session_type.lower() == session_type.lower():
                return session
        return None

    def get_race_session(self) -> Optional[F1Session]:
        """Get the main race session"""
        return self.get_session_by_type("race")

    def get_qualifying_session(self) -> Optional[F1Session]:
        """Get the qualifying session"""
        return self.get_session_by_type("qualifying")

    def get_upcoming_sessions(self) -> List[F1Session]:
        """Get sessions that haven't been completed yet"""
        now = datetime.now()
        upcoming = []
        for session in self.sessions:
            if not session.completed:
                # Simple date comparison (would need proper datetime parsing in production)
                session_datetime = datetime.strptime(f"{session.date} {session.time}", "%Y-%m-%d %H:%M:%S")
                if session_datetime > now:
                    upcoming.append(session)
        return upcoming

    def to_dict(self) -> Dict:
        """Convert Grand Prix to dictionary"""
        return {
            "grand_prix_id": self.grand_prix_id,
            "year": self.year,
            "round_number": self.round_number,
            "country": self.country,
            "circuit": self.circuit.to_dict(),
            "sessions": [session.to_dict() for session in self.sessions],
            "is_sprint_weekend": self.is_sprint_weekend,
            "official_name": self.official_name
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'F1GrandPrix':
        """Create Grand Prix from dictionary"""
        circuit = F1Circuit.from_dict(data["circuit"])
        sessions = [F1Session.from_dict(session_data) for session_data in data["sessions"]]
        return cls(
            grand_prix_id=data["grand_prix_id"],
            year=data["year"],
            round_number=data["round_number"],
            country=data["country"],
            circuit=circuit,
            sessions=sessions,
            is_sprint_weekend=data.get("is_sprint_weekend", False),
            official_name=data.get("official_name")
        )

class F1Season:
    """Model for F1 Season containing multiple Grand Prix"""
    def __init__(self, year: int, grand_prix_list: List[F1GrandPrix]):
        self.year = year
        self.grand_prix_list = grand_prix_list

    def get_grand_prix_by_id(self, grand_prix_id: str) -> Optional[F1GrandPrix]:
        """Get Grand Prix by ID"""
        for gp in self.grand_prix_list:
            if gp.grand_prix_id == grand_prix_id:
                return gp
        return None

    def get_upcoming_grand_prix(self) -> List[F1GrandPrix]:
        """Get Grand Prix that haven't started yet"""
        now = datetime.now()
        upcoming = []
        for gp in self.grand_prix_list:
            first_session = gp.sessions[0]  # Typically FP1 is first
            session_datetime = datetime.strptime(f"{first_session.date} {first_session.time}", "%Y-%m-%d %H:%M:%S")
            if session_datetime > now:
                upcoming.append(gp)
        return upcoming

    def get_current_or_next_grand_prix(self) -> Optional[F1GrandPrix]:
        """Get the current or next Grand Prix"""
        upcoming = self.get_upcoming_grand_prix()
        if upcoming:
            return upcoming[0]  # Next Grand Prix
        
        # If no upcoming, return the most recent one
        if self.grand_prix_list:
            return self.grand_prix_list[-1]
        return None

    def to_dict(self) -> Dict:
        """Convert season to dictionary"""
        return {
            "year": self.year,
            "grand_prix_list": [gp.to_dict() for gp in self.grand_prix_list]
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'F1Season':
        """Create season from dictionary"""
        grand_prix_list = [F1GrandPrix.from_dict(gp_data) for gp_data in data["grand_prix_list"]]
        return cls(
            year=data["year"],
            grand_prix_list=grand_prix_list
        )