import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pytz
from flask import current_app


class BettingManager:
    """Manager for handling user bets on F1 races."""

    def __init__(self, data_file: str = None):
        self.data_file = data_file or os.path.join(
            os.path.dirname(__file__), "data", "bets.json"
        )
        self._ensure_data_file_exists()

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

    def _ensure_data_file_exists(self):
        """Ensure the bets.json file exists with default structure."""
        if os.path.exists(self.data_file):
            return

        try:
            default_data = {
                "bets": {},
                "races": {},
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

            data.setdefault("bets", {})
            data.setdefault("races", {})
            data.setdefault("metadata", {})

            self._logger().debug(
                "Loaded betting data with %s user bets", len(data.get("bets", {}))
            )
            return data
        except (json.JSONDecodeError, IOError) as e:
            self._logger().error("Error loading bets: %s", e)
            return {"bets": {}, "races": {}, "metadata": {}}

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
                "Saved betting data: %s user bets", len(data.get("bets", {}))
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

    def place_bet(self, username: str, race_id: str, bets: List[str]) -> bool:
        """
        Place a bet for a user on a specific race.

        Args:
            username: Username placing the bet
            race_id: ID of the race being bet on
            bets: List of 3 driver IDs for positions 1, 2, 3

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

        try:
            data = self.load_bets()

            data["bets"].setdefault(username, {})

            data["bets"][username][race_id] = {
                "drivers": bets,
                "timestamp": self._now_iso(),
                "status": "active",
            }

            data["races"].setdefault(
                race_id,
                {
                    "users": [],
                    "created_at": self._now_iso(),
                    "status": "active",
                },
            )

            if username not in data["races"][race_id]["users"]:
                data["races"][race_id]["users"].append(username)

            self.save_bets(data)
            self._logger().info("Bet placed: %s on %s - %s", username, race_id, bets)
            return True

        except Exception as e:
            self._logger().error("Error placing bet for %s: %s", username, e)
            return False

    def get_user_bets(self, username: str) -> Dict:
        """Get all bets for a specific user."""
        try:
            data = self.load_bets()
            return data["bets"].get(username, {})
        except Exception as e:
            self._logger().error("Error getting bets for %s: %s", username, e)
            return {}

    def get_race_bets(self, race_id: str) -> Dict:
        """Get all bets for a specific race."""
        try:
            data = self.load_bets()
            race_bets = {}

            for username, user_bets in data["bets"].items():
                if race_id in user_bets:
                    race_bets[username] = user_bets[race_id]

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
            
            # Close all active bets for this race
            for username, user_bets in data["bets"].items():
                if race_id in user_bets and user_bets[race_id].get("status") == "active":
                    user_bets[race_id]["status"] = "closed"
                    user_bets[race_id]["closed_at"] = self._now_iso()
                    user_bets[race_id]["closed_by"] = "system"
                    bets_closed = True
                    self._logger().info("Closed bet for %s on %s (race started)", username, race_id)
            
            # Mark race as closed in race tracking
            if race_id in data["races"]:
                if data["races"][race_id].get("status") == "active":
                    data["races"][race_id]["status"] = "closed"
                    data["races"][race_id]["closed_at"] = self._now_iso()
                    bets_closed = True
                    self._logger().info("Marked race %s as closed (started)", race_id)
            else:
                # Create race entry if it doesn't exist
                data["races"][race_id] = {
                    "status": "closed",
                    "closed_at": self._now_iso(),
                    "users": []
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
                if race_id in data["races"]:
                    race_status = data["races"][race_id].get("status")
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
        Resolve a race and calculate points for users.

        Args:
            race_id: ID of the race to resolve
            actual_results: List of 3 driver IDs in actual finishing order

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

            race_bets = {}
            for username, user_bets in data["bets"].items():
                if race_id in user_bets:
                    race_bets[username] = user_bets[race_id]

            for username, bet_data in race_bets.items():
                if bet_data.get("status") != "active":
                    continue

                user_bets = bet_data.get("drivers", [])
                points = 0

                for i, predicted_driver in enumerate(user_bets):
                    if predicted_driver in actual_results:
                        actual_position = actual_results.index(predicted_driver)
                        if i == actual_position:
                            points += 5
                        else:
                            points += 2

                bet_data["status"] = "resolved"
                bet_data["resolved_at"] = self._now_iso()
                bet_data["actual_results"] = actual_results
                bet_data["points_awarded"] = points

                data["bets"].setdefault(username, {})
                data["bets"][username][race_id] = bet_data

                points_summary[username] = points
                self._logger().info(
                    "Resolved bet for %s on %s: %s points", username, race_id, points
                )

            if race_id in data["races"]:
                data["races"][race_id]["status"] = "resolved"
                data["races"][race_id]["resolved_at"] = self._now_iso()
                data["races"][race_id]["results"] = actual_results

            self.save_bets(data)
            return points_summary

        except Exception as e:
            self._logger().error("Error resolving race %s: %s", race_id, e)
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
            if race_id in data["races"]:
                race_status = data["races"][race_id].get("status")
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


betting_manager = BettingManager()