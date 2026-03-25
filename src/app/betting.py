import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pytz
import requests
from flask import current_app


class BettingManager:
    """Manager for handling user bets on F1 races."""

    def __init__(self, data_file: str = None):
        self.data_file = data_file or os.path.join(
            os.path.dirname(__file__), "data", "bets.json"
        )
        self.drivers_file = os.path.join(
            os.path.dirname(__file__), "data", "drivers.json"
        )
        self._ensure_data_file_exists()
        self._load_driver_data()

    def _logger(self):
        try:
            return current_app.logger
        except RuntimeError:
            # No app context, use module logger
            return logging.getLogger(__name__)

    def _utc_now(self) -> datetime:
        return datetime.now(pytz.UTC)

    def _now_iso(self) -> str:
        return self._utc_now().isoformat()

    def _load_driver_data(self):
        """Load driver data for team lookup."""
        try:
            if os.path.exists(self.drivers_file):
                with open(self.drivers_file, "r", encoding="utf-8") as f:
                    driver_data = json.load(f)
                    # Create driver_id -> team mapping
                    self.driver_teams = {}
                    for driver in driver_data.get("drivers", []):
                        driver_id = driver.get("driverId")
                        team_id = driver.get("teamId")
                        if driver_id and team_id:
                            self.driver_teams[driver_id] = team_id
            else:
                self.driver_teams = {}
                self._logger().warning("Driver data file not found: %s", self.drivers_file)
        except Exception as e:
            self.driver_teams = {}
            self._logger().error("Error loading driver data: %s", e)

    def _get_users_file(self) -> str:
        """Get path to users data file."""
        return os.path.join(os.path.dirname(self.data_file), 'users.json')

    def load_users(self) -> Dict:
        """Load all user data from file."""
        try:
            users_file = self._get_users_file()
            if not os.path.exists(users_file):
                return {"users": {}}

            with open(users_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            data.setdefault("users", {})
            self._logger().debug(
                "Loaded user data with %s users", len(data.get("users", {}))
            )
            return data
        except (json.JSONDecodeError, IOError) as e:
            self._logger().error("Error loading users: %s", e)
            return {"users": {}}

    def save_users(self, data: Dict):
        """Save user data to file with backup."""
        try:
            users_file = self._get_users_file()
            backup_file = users_file + ".bak"
            
            # Create backup
            if os.path.exists(users_file):
                with open(users_file, "r", encoding="utf-8") as f:
                    backup_data = json.load(f)
                with open(backup_file, "w", encoding="utf-8") as f:
                    json.dump(backup_data, f, indent=2)

            # Save new data
            with open(users_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            self._logger().info(
                "Saved user data: %s users", len(data.get("users", {}))
            )

            # Remove backup
            if os.path.exists(backup_file):
                os.remove(backup_file)

        except Exception as e:
            self._logger().error("Error saving users: %s", e)
            
            # Try to restore from backup
            if os.path.exists(backup_file):
                try:
                    with open(backup_file, "r", encoding="utf-8") as f:
                        restored_data = json.load(f)
                    with open(users_file, "w", encoding="utf-8") as f:
                        json.dump(restored_data, f, indent=2)
                    os.remove(backup_file)
                    self._logger().error("Restored from backup after save failure")
                except Exception as restore_error:
                    self._logger().error(
                        "Failed to restore backup after save failure: %s", restore_error
                    )
            raise

    def _ensure_data_file_exists(self):
        """Ensure the bets.json file exists with default structure."""
        if os.path.exists(self.data_file):
            return

        try:
            default_data = {
                "race_bets": {},
                "metadata": {
                    "created_at": self._now_iso(),
                    "version": "1.0",
                },
            }

            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)

            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(default_data, f, indent=2)

            self._logger().info("Created new bets file: %s", self.data_file)
        except Exception as e:
            self._logger().error("Error creating bets file: %s", e)
            raise

    def is_betting_closed(self, race_id: str) -> bool:
        from .race_data import race_data_manager

        race = race_data_manager.get_race_by_id(race_id)
        if not race:
            return True

        race_datetime = race_data_manager._get_race_datetime(race)
        if not race_datetime:
            return True

        now = datetime.now(pytz.UTC)

        # Optional safety buffer
        BUFFER = timedelta(minutes=2)

        return race_datetime - BUFFER <= now

    def load_bets(self) -> Dict:
        """Load all betting data from file."""
        try:
            if not os.path.exists(self.data_file):
                self._ensure_data_file_exists()

            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            data.setdefault("race_bets", {})
            data.setdefault("metadata", {})

            self._logger().debug(
                "Loaded betting data with %s race bets", len(data.get("race_bets", {}))
            )
            return data
        except (json.JSONDecodeError, IOError) as e:
            self._logger().error("Error loading bets: %s", e)
            return {"race_bets": {}, "metadata": {}}

    def save_bets(self, data: Dict):
        """Save betting data to file with a backup."""
        backup_file = self.data_file + ".bak"
        try:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)

            if os.path.exists(self.data_file):
                with open(self.data_file, "r", encoding="utf-8") as f:
                    backup_data = json.load(f)
                with open(backup_file, "w", encoding="utf-8") as f:
                    json.dump(backup_data, f, indent=2)

            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            self._logger().info(
                "Saved betting data: %s race bets", len(data.get("race_bets", {}))
            )

            if os.path.exists(backup_file):
                os.remove(backup_file)

        except Exception as e:
            self._logger().error("Error saving bets: %s", e)

            if os.path.exists(backup_file):
                try:
                    with open(backup_file, "r", encoding="utf-8") as f:
                        restored_data = json.load(f)
                    with open(self.data_file, "w", encoding="utf-8") as f:
                        json.dump(restored_data, f, indent=2)
                    os.remove(backup_file)
                    self._logger().error("Restored from backup after save failure")
                except Exception as restore_error:
                    self._logger().error(
                        "Failed to restore backup after save failure: %s", restore_error
                    )
            raise

    def _update_user_scores(self, race_id: str, points_summary: Dict):
        """
        Update user scores in users.json after race resolution.
        
        Args:
            race_id: ID of the resolved race
            points_summary: Dictionary of username -> points awarded
        """
        try:
            # Load current user data
            users_data = self.load_users()
            
            # Update each user's score
            for username, points_data in points_summary.items():
                if username in users_data["users"]:
                    # Get current score
                    current_score = users_data["users"][username].get("score", 0)
                    
                    # Add new points
                    if isinstance(points_data, dict):
                        total_points = points_data.get("total", 0)
                    else:
                        total_points = points_data
                    
                    # Update score
                    users_data["users"][username]["score"] = current_score + total_points
                    
                    # Add to score history
                    score_history = users_data["users"][username].setdefault("score_history", [])
                    score_history.append({
                        "race_id": race_id,
                        "points": total_points,
                        "total": current_score + total_points,
                        "timestamp": self._now_iso()
                    })
                    
                    self._logger().info(
                        "Updated score for %s: %s -> %s (+%s)", 
                        username, current_score, current_score + total_points, total_points
                    )
            
            # Save updated user data
            self.save_users(users_data)
            
        except Exception as e:
            self._logger().error("Error updating user scores: %s", e)

    def calculate_points(self, user_bet: Dict, actual_results: Dict) -> Dict:
        """
        Calculate points based on the scoring rules:
        - 1 point per correct driver position
        - 1 point per correct team position  
        - 1 point for correct fastest lap
        - 1 bonus point for perfect podium (all drivers AND teams correct)
        
        Args:
            user_bet: User's bet with drivers and fastest_lap
            actual_results: Race results with full driver/team data
            
        Returns:
            Dict with total points and breakdown by category
        """
        points = 0
        breakdown = {
            'position_1': 0,
            'position_2': 0,
            'position_3': 0,
            'fastest_lap': 0,
            'perfect_podium': 0
        }
        
        # Extract actual results data
        actual_positions = []
        actual_teams = []
        actual_fastest_lap = None
        
        for result in actual_results.get('results', []):
            if len(actual_positions) >= 3:
                break
            actual_positions.append(result.get('driverId'))
            actual_teams.append(result.get('teamId'))
        
        # Find fastest lap driver
        fastest_lap_data = actual_results.get('overall_fastest_lap', {})
        if fastest_lap_data:
            actual_fastest_lap = fastest_lap_data.get('driverId')
        
        # Check each position (1st, 2nd, 3rd)
        perfect_podium = True
        
        for i in range(3):
            if i >= len(user_bet.get('drivers', [])):
                continue
                
            bet_driver = user_bet['drivers'][i]
            
            # Check if position exists in actual results
            if i < len(actual_positions):
                actual_driver = actual_positions[i]
                actual_team = actual_teams[i]
                
                # Get team for bet driver
                bet_team = self.driver_teams.get(bet_driver)
                
                # Award 1 point for correct driver
                if bet_driver == actual_driver:
                    points += 1
                    breakdown[f'position_{i+1}'] += 1
                
                # Award 1 point for correct team
                if bet_team == actual_team:
                    points += 1
                    breakdown[f'position_{i+1}'] += 1
                
                # Check if this position breaks perfect podium
                if bet_driver != actual_driver or bet_team != actual_team:
                    perfect_podium = False
        
        # Check fastest lap
        if user_bet.get('fastest_lap') == actual_fastest_lap:
            points += 1
            breakdown['fastest_lap'] = 1
        
        # Award perfect podium bonus
        if perfect_podium:
            points += 1
            breakdown['perfect_podium'] = 1
        
        return {
            'total_points': points,
            'breakdown': breakdown
        }

    def place_bet(self, username: str, race_id: str, bets: List[str], fastest_lap: str = None) -> bool:
        """
        Place a bet for a user on a specific race.

        Args:
            username: Username placing the bet
            race_id: ID of the race being bet on
            bets: List of 3 driver IDs for positions 1, 2, 3
            fastest_lap: Driver ID for fastest lap prediction

        Returns:
            True if bet was placed successfully, False otherwise
        """
        if len(bets) != 3:
            self._logger().warning(
                "Invalid bet length for %s on %s: %s", username, race_id, len(bets)
            )
            return False

        if len(set(bets)) != 3:
            self._logger().warning(
                "Duplicate drivers in bet for %s on %s", username, race_id
            )
            return False

        if not fastest_lap:
            self._logger().warning(
                "Fastest lap not selected for %s on %s", username, race_id
            )
            return False

        try:
            data = self.load_bets()

            # Create bet data
            bet_data = {
                "drivers": bets,
                "fastest_lap": fastest_lap,
                "created_at": self._now_iso()
            }

            # Store bet in race_bets[race_id].user_bets[username] structure
            data["race_bets"].setdefault(race_id, {
                "user_bets": {},
                "status": "active",
            })

            data["race_bets"][race_id]["user_bets"][username] = bet_data

            self.save_bets(data)
            self._logger().info("Bet placed: %s on %s - %s (Fastest Lap: %s)", username, race_id, bets, fastest_lap or "None")
            return True

        except Exception as e:
            self._logger().error("Error placing bet for %s: %s", username, e)
            return False

    def get_user_bets(self, username: str) -> Dict:
        """Get all bets for a specific user."""
        try:
            data = self.load_bets()
            user_bets = {}
            
            # New structure: bets are nested under race_bets[race_id].user_bets[username]
            for race_id, race_data in data["race_bets"].items():
                if "user_bets" in race_data and username in race_data["user_bets"]:
                    user_bets[race_id] = race_data["user_bets"][username]
            
            return user_bets
        except Exception as e:
            self._logger().error("Error getting bets for %s: %s", username, e)
            return {}

    def get_race_bets(self, race_id: str) -> Dict:
        """Get all bets for a specific race."""
        try:
            data = self.load_bets()
            race_bets = {}

            # New structure: bets are nested under race_bets[race_id].user_bets
            if race_id in data["race_bets"] and "user_bets" in data["race_bets"][race_id]:
                race_bets = data["race_bets"][race_id]["user_bets"]

            return race_bets
        except Exception as e:
            self._logger().error("Error getting bets for race %s: %s", race_id, e)
            return {}

    def get_all_bets(self) -> Dict:
        """Get all betting data."""
        return self.load_bets()

    def close_bets_for_race(self, race_id: str) -> bool:
        """
        Close all bets for a race when the race weekend starts.
        
        This method should be called automatically when a race begins.
        Once closed, bets cannot be edited or canceled.
        
        Args:
            race_id: ID of the race to close bets for
            
        Returns:
            bool: True if bets were closed successfully
        """
        try:
            data = self.load_bets()
            bets_closed = False
            
            # Close all bets for this race - new structure
            if race_id in data["race_bets"] and "user_bets" in data["race_bets"][race_id]:
                for username, bet_data in data["race_bets"][race_id]["user_bets"].items():
                    # Remove individual bet timestamps when closing
                    bet_data.pop("closed_at", None)
                    bet_data.pop("closed_by", None)
                    bets_closed = True
                    self._logger().info("Closed bet for %s on %s (race started)", username, race_id)
            
            # Mark race as closed in race tracking
            if race_id in data["race_bets"]:
                if data["race_bets"][race_id].get("status") == "active":
                    data["race_bets"][race_id]["status"] = "closed"
                    data["race_bets"][race_id]["closed_at"] = self._now_iso()
                    bets_closed = True
                    self._logger().info("Marked race %s as closed (started)", race_id)
            else:
                # Create race entry if it doesn't exist
                data["race_bets"][race_id] = {
                    "status": "closed",
                    "closed_at": self._now_iso(),
                    "user_bets": {}
                }
                bets_closed = True
                self._logger().info("Created closed race entry for %s", race_id)
            
            if bets_closed:
                self.save_bets(data)
            
            return bets_closed
            
        except Exception as e:
            self._logger().error("Error closing bets for race %s: %s", race_id, e)
            return False

    def check_and_close_expired_bets(self):
        """
        Check all races and automatically close bets for races that have started.
        
        This should be called regularly (e.g., on page load) to ensure bets
        are properly closed when race weekends begin.
        
        Returns:
            int: Number of races that had bets closed
        """
        try:
            from .race_data import race_data_manager
            
            data = self.load_bets()
            all_races = race_data_manager.get_all_races()
            now = self._utc_now()
            races_closed = 0
            
            for race in all_races:
                race_id = race.get("id")
                if not race_id:
                    continue
                
                # Skip if race is already closed or resolved
                if race_id in data["race_bets"]:
                    race_status = data["race_bets"][race_id].get("status")
                    if race_status in ["closed", "resolved"]:
                        continue
                
                # Check if race has started
                race_datetime = race_data_manager._get_race_datetime(race)
                if race_datetime and race_datetime <= now:
                    # Race has started, close bets
                    if self.close_bets_for_race(race_id):
                        races_closed += 1
            
            if races_closed > 0:
                self._logger().info("Automatically closed bets for %s races that have started", races_closed)
            
            return races_closed
            
        except Exception as e:
            self._logger().error("Error checking for expired bets: %s", e)
            return 0

    def resolve_race(self, race_id: str, actual_results: List[str]) -> Dict:
        """
        Resolve a race and calculate points for users using the new scoring system.

        Args:
            race_id: ID of the race to resolve
            actual_results: List of 3 driver IDs in actual finishing order

        Returns:
            Summary of points awarded by user with breakdowns
        """
        if len(actual_results) != 3:
            self._logger().warning(
                "Invalid results length for race %s: %s", race_id, len(actual_results)
            )
            return {}

        try:
            data = self.load_bets()
            points_summary = {}

            # New structure: get race bets from race_bets[race_id].user_bets
            race_bets = {}
            if race_id in data["race_bets"] and "user_bets" in data["race_bets"][race_id]:
                race_bets = data["race_bets"][race_id]["user_bets"]

            for username, bet_data in race_bets.items():
                # Create full actual results structure for scoring
                actual_results_full = {
                    'results': [
                        {'driverId': actual_results[0], 'teamId': self.driver_teams.get(actual_results[0])},
                        {'driverId': actual_results[1], 'teamId': self.driver_teams.get(actual_results[1])},
                        {'driverId': actual_results[2], 'teamId': self.driver_teams.get(actual_results[2])}
                    ]
                }
                
                # Calculate points using new scoring system
                points_data = self.calculate_points(bet_data, actual_results_full)
                points = points_data['total_points']
                
                bet_data["points_awarded"] = points
                bet_data["points_breakdown"] = points_data["breakdown"]

                # Update bet in new structure
                data["race_bets"][race_id]["user_bets"][username] = bet_data

                points_summary[username] = {
                    'total': points,
                    'breakdown': points_data['breakdown']
                }
                self._logger().info(
                    "Resolved bet for %s on %s: %s points (Breakdown: %s)", 
                    username, race_id, points, points_data['breakdown']
                )

            if race_id in data["race_bets"]:
                data["race_bets"][race_id]["status"] = "resolved"
                data["race_bets"][race_id]["resolved_at"] = self._now_iso()

            self.save_bets(data)
            
            # Update user scores in users.json
            self._update_user_scores(race_id, points_summary)
            
            return points_summary

        except Exception as e:
            self._logger().error("Error resolving race %s: %s", race_id, e)
            return {}

    def resolve_race_with_fastest_lap(self, race_id: str, actual_results: List[str], fastest_lap_driver: str = None) -> Dict:
        """
        Resolve a race including fastest lap predictions.
        
        Args:
            race_id: ID of the race to resolve
            actual_results: List of 3 driver IDs in actual finishing order
            fastest_lap_driver: Driver ID for fastest lap
            
        Returns:
            Summary of points awarded by user
        """
        if len(actual_results) != 3:
            self._logger().warning(
                "Invalid results length for race %s: %s", race_id, len(actual_results)
            )
            return {}

        try:
            data = self.load_bets()
            points_summary = {}

            # New structure: get race bets from race_bets[race_id].user_bets
            race_bets = {}
            if race_id in data["race_bets"] and "user_bets" in data["race_bets"][race_id]:
                race_bets = data["race_bets"][race_id]["user_bets"]

            for username, bet_data in race_bets.items():
                # Calculate points for positions
                points = 0
                # Create full actual results structure for new scoring system
                actual_results_full = {
                    'results': [
                        {'driverId': actual_results[0], 'teamId': self.driver_teams.get(actual_results[0])},
                        {'driverId': actual_results[1], 'teamId': self.driver_teams.get(actual_results[1])},
                        {'driverId': actual_results[2], 'teamId': self.driver_teams.get(actual_results[2])}
                    ]
                }
                
                # Add fastest lap to results if provided
                if fastest_lap_driver:
                    actual_results_full['overall_fastest_lap'] = {
                        'driverId': fastest_lap_driver,
                        'teamId': self.driver_teams.get(fastest_lap_driver)
                    }
                
                # Calculate points using new scoring system
                points_data = self.calculate_points(bet_data, actual_results_full)
                points = points_data['total_points']
                
                # Update bet with resolution results and detailed breakdown
                bet_data.update({
                    "actual_fastest_lap": fastest_lap_driver,
                    "points_awarded": points,
                    "points_breakdown": points_data['breakdown']
                })

                # Update bet in new structure
                data["race_bets"][race_id]["user_bets"][username] = bet_data

                points_summary[username] = {
                    'total': points,
                    'breakdown': points_data['breakdown']
                }
                self._logger().info(
                    "Resolved bet for %s on %s: %s points (Breakdown: %s)", 
                    username, race_id, points, points_data['breakdown']
                )

            if race_id in data["race_bets"]:
                data["race_bets"][race_id]["status"] = "resolved"
                data["race_bets"][race_id]["resolved_at"] = self._now_iso()

            self.save_bets(data)
            
            # Update user scores in users.json
            self._update_user_scores(race_id, points_summary)
            
            return points_summary

        except Exception as e:
            self._logger().error("Error resolving race %s with fastest lap: %s", race_id, e)
            return {}

    def update_user_score(self, username: str, points: int, race_id: str) -> bool:
        """
        Update a user's score based on betting results.
        """
        try:
            from .utils import load_users, save_users

            users = load_users()
            if username not in users:
                self._logger().warning("User not found for score update: %s", username)
                return False

            users[username].setdefault("score_history", [])
            users[username]["score"] = users[username].get("score", 0) + points

            users[username]["score_history"].append(
                {
                    "race_id": race_id,
                    "points": points,
                    "total": users[username]["score"],
                    "timestamp": self._now_iso(),
                }
            )

            save_users(users)
            self._logger().info(
                "Updated score for %s: +%s = %s",
                username,
                points,
                users[username]["score"],
            )
            return True

        except Exception as e:
            self._logger().error("Error updating score for %s: %s", username, e)
            return False

    def can_bet_on_race(self, race_id: str, username: str = None) -> bool:
        """
        Check if betting is allowed on a race.
        """
        try:
            from .race_data import race_data_manager

            race = race_data_manager.get_race_by_id(race_id)
            if not race:
                self._logger().warning("Race not found: %s", race_id)
                return False

            canceled_ids = race_data_manager.get_canceled_race_ids()
            if race_id in canceled_ids or race.get("canceled"):
                self._logger().warning("Race %s is canceled", race_id)
                return False

            race_datetime = race_data_manager._get_race_datetime(race)
            now = self._utc_now()

            if race_datetime is None:
                self._logger().warning("Could not parse race datetime for %s", race_id)
                return False

            if race_datetime <= now:
                self._logger().warning("Race %s has already started", race_id)
                return False

            if username:
                user_bets = self.get_user_bets(username)
                if race_id in user_bets:
                    self._logger().warning(
                        "User %s already has a bet on %s", username, race_id
                    )
                    return False

            data = self.load_bets()
            if race_id in data["race_bets"]:
                race_status = data["race_bets"][race_id].get("status")
                if race_status == "resolved":
                    self._logger().warning("Race %s is already resolved", race_id)
                    return False
                elif race_status == "closed":
                    self._logger().warning("Race %s is already closed (race weekend started)", race_id)
                    return False

            all_races = race_data_manager.get_all_races()
            upcoming_races = []

            for r in all_races:
                r_datetime = race_data_manager._get_race_datetime(r)
                if r_datetime and r_datetime > now and r.get("id") not in canceled_ids:
                    upcoming_races.append(
                        {"id": r["id"], "datetime": r_datetime, "name": r.get("name")}
                    )

            upcoming_races.sort(key=lambda x: x["datetime"])

            # Only allow betting on the very next race (first one only)
            if upcoming_races:
                allowed_race_id = upcoming_races[0]["id"]
                if race_id != allowed_race_id:
                    self._logger().warning(
                        "Betting not allowed on race %s - only the next race (%s) is open for betting",
                        race_id,
                        allowed_race_id,
                    )
                    return False

            return True

        except Exception as e:
            self._logger().error("Error checking bet eligibility for %s: %s", race_id, e)
            return False

    def get_available_drivers_for_race(self, race_id: str) -> List[Dict]:
        """
        Get list of available drivers for a specific race.
        """
        try:
            from .race_data import race_data_manager

            drivers_data = race_data_manager.load_drivers()
            drivers = drivers_data.get("drivers", [])

            formatted_drivers = []
            for driver in drivers:
                formatted_drivers.append(
                    {
                        "driver_id": driver.get("driverId"),
                        "name": f"{driver.get('name', '')} {driver.get('surname', '')}".strip(),
                        "short_name": driver.get("shortName", ""),
                        "number": driver.get("number", "N/A"),
                        "team": driver.get("teamId", "Unknown"),
                    }
                )

            return formatted_drivers

        except Exception as e:
            self._logger().error("Error getting drivers for race %s: %s", race_id, e)
            return []

    def _get_race_results_cache_file(self) -> str:
        """Get the path to the race results cache file."""
        return os.path.join(os.path.dirname(self.data_file), "race_results.json")

    def _load_race_results_cache(self) -> Dict:
        """Load race results from cache file."""
        cache_file = self._get_race_results_cache_file()
        
        if not os.path.exists(cache_file):
            return {}
        
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            self._logger().error("Error loading race results cache: %s", e)
            return {}

    def _save_race_results_cache(self, results: Dict):
        """Save race results to cache file."""
        cache_file = self._get_race_results_cache_file()
        
        try:
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
            self._logger().info("Saved race results cache to %s", cache_file)
        except Exception as e:
            self._logger().error("Error saving race results cache: %s", e)

    def fetch_race_results_from_api(self, race_id: str) -> Optional[Dict]:
        """
        Fetch race results from F1 API and cache them.
        Race ID format should be like 'bahrain_2026' which translates to year=2026, round=1
        """
        import requests
        
        # Parse race_id to get year and round
        # Expected format: country_year (e.g., bahrain_2026)
        try:
            parts = race_id.split('_')
            if len(parts) < 2:
                self._logger().error("Invalid race_id format: %s", race_id)
                return None
            
            year = parts[-1]  # Last part is year
            
            # Get round number from race data
            from .race_data import race_data_manager
            race = race_data_manager.get_race_by_id(race_id)
            
            if not race:
                self._logger().error("Race not found: %s", race_id)
                return None
            
            round_number = race.get('round')
            if not round_number:
                self._logger().error("Race missing round number: %s", race_id)
                return None
            
            # Fetch from F1 API
            api_url = f"https://f1api.dev/api/{year}/{round_number}/race"
            self._logger().info("Fetching race results from %s", api_url)
            
            response = requests.get(api_url, timeout=10)
            
            if response.status_code == 200:
                results_data = response.json()
                
                # Transform the results into our standard format
                transformed_results = self._transform_race_results(race_id, results_data)
                
                # Cache the transformed results (store the full transformed object)
                cache = self._load_race_results_cache()
                cache[race_id] = transformed_results  # Store the complete transformed results
                self._save_race_results_cache(cache)
                
                return transformed_results
            else:
                self._logger().error("API request failed with status %s: %s", 
                                   response.status_code, response.text)
                return None
                
        except Exception as e:
            self._logger().error("Error fetching race results for %s: %s", race_id, e)
            return None

    def get_race_results(self, race_id: str) -> Optional[Dict]:
        """
        Get race results, first from cache, then from API if not cached.
        """
        # First try cache
        cache = self._load_race_results_cache()
        cached_results = cache.get(race_id)
        
        if cached_results:
            self._logger().info("Using cached race results for %s", race_id)
            return cached_results  # Return the full transformed results object
        
        # If not in cache, fetch from API
        return self.fetch_race_results_from_api(race_id)

    def _transform_race_results(self, race_id: str, api_response: Dict) -> Dict:
        """
        Transform raw API response into structured race results format.
        
        Args:
            race_id: The race ID being transformed
            api_response: Raw response from F1 API
            
        Returns:
            Transformed results with consistent structure
        """
        try:
            # Get current timestamp
            transform_timestamp = self._now_iso()
            
            # Build API URL for reference
            from .race_data import race_data_manager
            race = race_data_manager.get_race_by_id(race_id)
            year = race.get('round')  # Actually round number, need to fix this
            
            # Parse race_id to get year (last part)
            year = race_id.split('_')[-1]
            round_number = race.get('round', 1)
            api_url = f"https://f1api.dev/api/{year}/{round_number}/race"
            
            # Transform results - handle both old and new API structures
            transformed_results = {
                'fetched_at': transform_timestamp,
                'api_url': api_url,
                'race_id': race_id,
                'results': []
            }
            
            # Check if this is the new API structure (with 'races' key)
            if 'races' in api_response:
                # New API structure: results are under races.results
                race_data = api_response['races']
                raw_results = race_data.get('results', [])
                
                # Extract race metadata
                transformed_results['race_date'] = race_data.get('date')
                transformed_results['race_time'] = race_data.get('time')
                transformed_results['race_name'] = race_data.get('raceName')
                
            else:
                # Old API structure: results are directly under 'results'
                raw_results = api_response.get('results', [])
            
            # Process each result
            for result in raw_results:
                # Handle both old and new structures for driver ID
                if 'driver' in result:
                    # New structure: driver info is nested
                    driver_id = result['driver'].get('driverId')
                    driver_name = f"{result['driver'].get('name', '')} {result['driver'].get('surname', '')}".strip()
                    driver_number = result['driver'].get('number')
                    
                    # Team info is also nested
                    team_id = result['team'].get('teamId')
                    team_name = result['team'].get('teamName')
                else:
                    # Old structure: driver info is at top level
                    driver_id = result.get('driverId')
                    driver_name = None
                    driver_number = None
                    team_id = result.get('constructor', {}).get('constructorId')
                    team_name = None
                
                # Handle fastest lap - different field names
                fast_lap_time = result.get('fastLap') or result.get('fastestLap', {}).get('time')
                
                transformed_result = {
                    'position': result.get('position'),
                    'driverId': driver_id,
                    'driverName': driver_name,
                    'driverNumber': driver_number,
                    'teamId': team_id,
                    'teamName': team_name,
                    'points': result.get('points', 0),
                    'status': result.get('status', 'Finished') if result.get('time') else 'DNF',
                    'fastLapTime': fast_lap_time
                }
                
                # Add fastest lap details if available
                if fast_lap_time:
                    transformed_result['fastestLap'] = {
                        'time': fast_lap_time
                    }
                    # If we have lap number, add it
                    if result.get('fastestLap'):
                        transformed_result['fastestLap']['lap'] = result['fastestLap'].get('lap')
                        transformed_result['fastestLap']['speed'] = result['fastestLap'].get('speed')
                
                transformed_results['results'].append(transformed_result)
            
            # Find overall fastest lap from individual results
            fastest_lap_driver = None
            fastest_lap_time = None
            
            for result in transformed_results['results']:
                if result.get('fastLapTime') and (fastest_lap_time is None or result['fastLapTime'] < fastest_lap_time):
                    fastest_lap_time = result['fastLapTime']
                    fastest_lap_driver = result['driverId']
            
            if fastest_lap_driver:
                transformed_results['overall_fastest_lap'] = {
                    'driverId': fastest_lap_driver,
                    'time': fastest_lap_time
                }
            
            return transformed_results
            
        except Exception as e:
            self._logger().error("Error transforming race results for %s: %s", race_id, e)
            # Return minimal structure on error
            return {
                'fetched_at': self._now_iso(),
                'api_url': f"https://f1api.dev/api/{race_id.split('_')[-1]}/1/race",
                'race_id': race_id,
                'results': [],
                'error': str(e)
            }

    def resolve_race_from_api(self, race_id: str) -> bool:
        """
        Resolve a race by fetching results from F1 API and updating bets.
        """
        try:
            # Get race results
            results = self.get_race_results(race_id)
            
            if not results:
                self._logger().error("No race results available for %s", race_id)
                return False
            
            # Extract top 3 drivers from transformed results
            # New structure: results['results'] contains list of transformed results
            race_results = results.get('results', [])
            
            if len(race_results) < 3:
                self._logger().error("Insufficient race results data for %s (got %s results)", race_id, len(race_results))
                # Check if this is an API issue vs empty results
                if len(race_results) == 0:
                    self._logger().warning("Race %s has no results available from API - race may be too far in future or API issue", race_id)
                return False
            
            # Get driver IDs for positions 1, 2, 3 from transformed structure
            actual_results = []
            for i in range(3):
                if i < len(race_results):
                    result = race_results[i]
                    driver_id = result.get('driverId')
                    if driver_id:
                        actual_results.append(driver_id)
                    else:
                        self._logger().warning("Race result at position %s for %s has no driverId", i+1, race_id)
            
            # Also extract fastest lap driver for complete resolution
            fastest_lap_driver = None
            overall_fastest = results.get('overall_fastest_lap')
            if overall_fastest:
                fastest_lap_driver = overall_fastest.get('driverId')
            
            # Fallback: find fastest lap from individual results
            if not fastest_lap_driver:
                for result in race_results:
                    if result.get('fastestLap'):
                        fastest_lap_driver = result.get('driverId')
                        break
            
            if len(actual_results) < 3:
                self._logger().error("Could not extract 3 drivers from race results for %s (only got %s)", race_id, len(actual_results))
                return False
            
            # Resolve the race with the actual results and fastest lap
            points_summary = self.resolve_race_with_fastest_lap(
                race_id, actual_results, fastest_lap_driver
            )
            
            if points_summary:
                # Update user scores
                for username, points in points_summary.items():
                    self.update_user_score(username, points, race_id)
                
                self._logger().info("Successfully resolved race %s with API results (including fastest lap)", race_id)
                return True
            else:
                self._logger().info("No bets to resolve for race %s", race_id)
                return True
                
        except Exception as e:
            self._logger().error("Error resolving race %s from API: %s", race_id, e)
            return False


betting_manager = BettingManager()
