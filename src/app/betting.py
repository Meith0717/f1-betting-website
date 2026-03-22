import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from flask import current_app
import pytz

class BettingManager:
    """Manager for handling user bets on F1 races"""

    def __init__(self, data_file: str = None):
        self.data_file = data_file or os.path.join(
            os.path.dirname(__file__), "data", "bets.json"
        )
        self._ensure_data_file_exists()

    def _ensure_data_file_exists(self):
        """Ensure the bets.json file exists with default structure"""
        if not os.path.exists(self.data_file):
            try:
                default_data = {
                    "bets": {},
                    "races": {},
                    "metadata": {
                        "created_at": datetime.now().isoformat(),
                        "version": "1.0"
                    }
                }
                
                # Create data directory if it doesn't exist
                os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
                
                with open(self.data_file, 'w') as f:
                    json.dump(default_data, f, indent=2)
                    
                current_app.logger.info(f"Created new bets file: {self.data_file}")
            except Exception as e:
                current_app.logger.error(f"Error creating bets file: {e}")
                raise

    def load_bets(self) -> Dict:
        """Load all betting data from file"""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                current_app.logger.debug(f"Loaded betting data with {len(data.get('bets', {}))} user bets")
                return data
        except (json.JSONDecodeError, IOError) as e:
            current_app.logger.error(f"Error loading bets: {e}")
            return {"bets": {}, "races": {}, "metadata": {}}

    def save_bets(self, data: Dict):
        """Save betting data to file"""
        try:
            # Create backup first
            backup_file = self.data_file + ".bak"
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    backup_data = json.load(f)
                with open(backup_file, 'w') as f:
                    json.dump(backup_data, f, indent=2)
            
            # Save new data
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            current_app.logger.info(f"Saved betting data: {len(data.get('bets', {}))} user bets")
            
            # Clean up backup
            if os.path.exists(backup_file):
                os.remove(backup_file)
                
        except Exception as e:
            current_app.logger.error(f"Error saving bets: {e}")
            # Try to restore from backup if it exists
            if os.path.exists(backup_file):
                with open(backup_file, 'r') as f:
                    restored_data = json.load(f)
                with open(self.data_file, 'w') as f:
                    json.dump(restored_data, f, indent=2)
                os.remove(backup_file)
                current_app.logger.error("Restored from backup after save failure")
            raise

    def place_bet(self, username: str, race_id: str, bets: List[str]) -> bool:
        """
        Place a bet for a user on a specific race
        
        Args:
            username: Username placing the bet
            race_id: ID of the race being bet on
            bets: List of 3 driver IDs for positions 1, 2, 3
        
        Returns:
            bool: True if bet was placed successfully, False otherwise
        """
        if len(bets) != 3:
            current_app.logger.warning(f"Invalid bet length for {username} on {race_id}: {len(bets)}")
            return False
        
        if len(set(bets)) != 3:
            current_app.logger.warning(f"Duplicate drivers in bet for {username} on {race_id}")
            return False
        
        try:
            data = self.load_bets()
            
            # Initialize user bets if not exists
            if username not in data["bets"]:
                data["bets"][username] = {}
            
            # Store the bet
            data["bets"][username][race_id] = {
                "drivers": bets,
                "timestamp": datetime.now().isoformat(),
                "status": "active"
            }
            
            # Track which races have bets
            if race_id not in data["races"]:
                data["races"][race_id] = {
                    "users": [],
                    "created_at": datetime.now().isoformat()
                }
            
            if username not in data["races"][race_id]["users"]:
                data["races"][race_id]["users"].append(username)
            
            self.save_bets(data)
            current_app.logger.info(f"Bet placed: {username} on {race_id} - {bets}")
            return True
            
        except Exception as e:
            current_app.logger.error(f"Error placing bet for {username}: {e}")
            return False

    def get_user_bets(self, username: str) -> Dict:
        """
        Get all bets for a specific user
        
        Args:
            username: Username to get bets for
        
        Returns:
            Dict: Dictionary of race_id -> bet_data
        """
        try:
            data = self.load_bets()
            return data["bets"].get(username, {})
        except Exception as e:
            current_app.logger.error(f"Error getting bets for {username}: {e}")
            return {}

    def get_race_bets(self, race_id: str) -> Dict:
        """
        Get all bets for a specific race
        
        Args:
            race_id: ID of the race
        
        Returns:
            Dict: Dictionary of username -> bet_data for this race
        """
        try:
            data = self.load_bets()
            race_bets = {}
            
            for username, user_bets in data["bets"].items():
                if race_id in user_bets:
                    race_bets[username] = user_bets[race_id]
            
            return race_bets
        except Exception as e:
            current_app.logger.error(f"Error getting bets for race {race_id}: {e}")
            return {}

    def get_all_bets(self) -> Dict:
        """
        Get all betting data
        
        Returns:
            Dict: Complete betting data structure
        """
        return self.load_bets()

    def resolve_race(self, race_id: str, actual_results: List[str]) -> Dict:
        """
        Resolve a race and calculate points for users
        
        Args:
            race_id: ID of the race to resolve
            actual_results: List of 3 driver IDs in actual finishing order
        
        Returns:
            Dict: Summary of points awarded
        """
        if len(actual_results) != 3:
            current_app.logger.warning(f"Invalid results length for race {race_id}: {len(actual_results)}")
            return {}
        
        try:
            data = self.load_bets()
            points_summary = {}
            
            # Get all bets for this race
            race_bets = self.get_race_bets(race_id)
            
            for username, bet_data in race_bets.items():
                if bet_data["status"] != "active":
                    continue
                
                user_bets = bet_data["drivers"]
                points = 0
                
                # Calculate points based on correct predictions
                for i, predicted_driver in enumerate(user_bets):
                    if predicted_driver in actual_results:
                        actual_position = actual_results.index(predicted_driver)
                        
                        # Points system:
                        # - Correct position: 5 points
                        # - Correct driver but wrong position: 2 points
                        if i == actual_position:
                            points += 5  # Correct position
                        else:
                            points += 2  # Correct driver, wrong position
                
                # Update bet status
                bet_data["status"] = "resolved"
                bet_data["resolved_at"] = datetime.now().isoformat()
                bet_data["actual_results"] = actual_results
                bet_data["points_awarded"] = points
                
                # Update user data
                data["bets"][username][race_id] = bet_data
                
                points_summary[username] = points
                current_app.logger.info(f"Resolved bet for {username} on {race_id}: {points} points")
            
            # Mark race as resolved
            if race_id in data["races"]:
                data["races"][race_id]["status"] = "resolved"
                data["races"][race_id]["resolved_at"] = datetime.now().isoformat()
                data["races"][race_id]["results"] = actual_results
            
            self.save_bets(data)
            return points_summary
            
        except Exception as e:
            current_app.logger.error(f"Error resolving race {race_id}: {e}")
            return {}

    def update_user_score(self, username: str, points: int, race_id: str) -> bool:
        """
        Update a user's score based on betting results
        
        Args:
            username: Username to update
            points: Points to add to user's score
            race_id: ID of the race that awarded these points
        
        Returns:
            bool: True if update was successful
        """
        try:
            from .utils import load_users, save_users
            
            users = load_users()
            if username not in users:
                current_app.logger.warning(f"User not found for score update: {username}")
                return False
            
            # Initialize score history if not exists
            if "score_history" not in users[username]:
                users[username]["score_history"] = []
            
            # Update score
            users[username]["score"] = users[username].get("score", 0) + points
            
            # Record the score change
            users[username]["score_history"].append({
                "race_id": race_id,
                "points": points,
                "total": users[username]["score"],
                "timestamp": datetime.now().isoformat()
            })
            
            save_users(users)
            current_app.logger.info(f"Updated score for {username}: +{points} = {users[username]['score']}")
            return True
            
        except Exception as e:
            current_app.logger.error(f"Error updating score for {username}: {e}")
            return False

    def can_bet_on_race(self, race_id: str, username: str = None) -> bool:
        """
        Check if betting is allowed on a race
        
        Args:
            race_id: ID of the race to check
            username: Optional username to check if they already have a bet
        
        Returns:
            bool: True if betting is allowed
        """
        try:
            from .race_data import race_data_manager
            
            # Get race data
            race = race_data_manager.get_race_by_id(race_id)
            if not race:
                current_app.logger.warning(f"Race not found: {race_id}")
                return False
            
            # Check if race has already started
            race_datetime = race_data_manager._get_race_datetime(race)
            if race_datetime and race_datetime < datetime.now(pytz.UTC):
                current_app.logger.warning(f"Race {race_id} has already started")
                return False
            
            # Check if race is canceled
            canceled_ids = race_data_manager.get_canceled_race_ids()
            if race_id in canceled_ids:
                current_app.logger.warning(f"Race {race_id} is canceled")
                return False
            
            # Check if user already has a bet (if username provided)
            if username:
                user_bets = self.get_user_bets(username)
                if race_id in user_bets:
                    current_app.logger.warning(f"User {username} already has a bet on {race_id}")
                    return False
            
            # Check if race is already resolved
            data = self.load_bets()
            if race_id in data["races"] and data["races"][race_id].get("status") == "resolved":
                current_app.logger.warning(f"Race {race_id} is already resolved")
                return False
            
            # Only allow betting on the next race weekend (current + next 2 races)
            all_races = race_data_manager.get_all_races()
            upcoming_races = []
            
            for r in all_races:
                r_datetime = race_data_manager._get_race_datetime(r)
                if r_datetime and r_datetime > datetime.now(pytz.UTC):
                    # Check if race is not canceled
                    if r["id"] not in canceled_ids:
                        upcoming_races.append({
                            "id": r["id"],
                            "datetime": r_datetime,
                            "name": r["name"]
                        })
            
            # Sort by date
            upcoming_races.sort(key=lambda x: x["datetime"])
            
            # Only allow betting on the first 3 upcoming race weekends
            if len(upcoming_races) > 3:
                allowed_race_ids = [r["id"] for r in upcoming_races[:3]]
                if race_id not in allowed_race_ids:
                    current_app.logger.warning(f"Betting not allowed on race {race_id} - only next 3 race weekends are open for betting")
                    return False
            
            return True
            
        except Exception as e:
            current_app.logger.error(f"Error checking bet eligibility for {race_id}: {e}")
            return False

    def get_available_drivers_for_race(self, race_id: str) -> List[Dict]:
        """
        Get list of available drivers for a specific race
        
        Args:
            race_id: ID of the race
        
        Returns:
            List[Dict]: List of driver information
        """
        try:
            from .race_data import race_data_manager
            
            # Get drivers from race data manager
            drivers_data = race_data_manager.load_drivers()
            drivers = drivers_data.get("drivers", [])
            
            # Format driver data for betting interface
            formatted_drivers = []
            for driver in drivers:
                formatted_drivers.append({
                    "driver_id": driver["driverId"],
                    "name": f"{driver['name']} {driver['surname']}",
                    "short_name": driver["shortName"],
                    "number": driver.get("number", "N/A"),
                    "team": driver.get("teamId", "Unknown")
                })
            
            return formatted_drivers
            
        except Exception as e:
            current_app.logger.error(f"Error getting drivers for race {race_id}: {e}")
            return []


# Initialize the betting manager
betting_manager = BettingManager()