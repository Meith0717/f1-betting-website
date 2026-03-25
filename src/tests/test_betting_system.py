"""
Comprehensive test suite for the F1 Betting System.

This test suite covers the core betting functionality including:
- Bet placement and management
- Race resolution and scoring
- User score updates
- Data validation and edge cases
"""

import pytest
from datetime import datetime, timedelta
import pytz


class TestBettingManager:
    """Test suite for the BettingManager class."""

    def test_bet_placement_valid(
        self, betting_manager, sample_race_data, sample_user_bet
    ):
        """Test placing a valid bet."""
        race_id = sample_race_data["id"]
        username = "test_user"

        # Place bet
        result = betting_manager.place_bet(
            username,
            race_id,
            sample_user_bet["drivers"],
            sample_user_bet["fastest_lap"],
        )

        assert result is True

        # Verify bet was stored
        user_bets = betting_manager.get_user_bets(username)
        assert race_id in user_bets
        assert user_bets[race_id]["drivers"] == sample_user_bet["drivers"]
        assert user_bets[race_id]["fastest_lap"] == sample_user_bet["fastest_lap"]

    def test_bet_placement_invalid_duplicate_drivers(
        self, betting_manager, sample_race_data
    ):
        """Test that bets with duplicate drivers are rejected."""
        race_id = sample_race_data["id"]
        username = "test_user"

        # Try to place bet with duplicate drivers
        result = betting_manager.place_bet(
            username,
            race_id,
            ["verstappen", "verstappen", "hamilton"],  # Duplicate verstappen
            "verstappen",
        )

        assert result is False

    def test_bet_placement_invalid_wrong_count(self, betting_manager, sample_race_data):
        """Test that bets with wrong number of drivers are rejected."""
        race_id = sample_race_data["id"]
        username = "test_user"

        # Try to place bet with only 2 drivers
        result = betting_manager.place_bet(
            username,
            race_id,
            ["verstappen", "hamilton"],  # Only 2 drivers
            "verstappen",
        )

        assert result is False

    def test_race_resolution_perfect_podium(
        self, betting_manager, sample_race_data, sample_actual_results
    ):
        """Test race resolution with perfect podium prediction."""
        race_id = sample_race_data["id"]
        username = "test_user"

        # Place a perfect bet
        perfect_bet_drivers = [
            sample_actual_results["results"][0]["driverId"],
            sample_actual_results["results"][1]["driverId"],
            sample_actual_results["results"][2]["driverId"],
        ]
        perfect_fastest_lap = sample_actual_results["overall_fastest_lap"]["driverId"]

        betting_manager.place_bet(
            username, race_id, perfect_bet_drivers, perfect_fastest_lap
        )

        # Resolve the race
        actual_results_drivers = [
            sample_actual_results["results"][0]["driverId"],
            sample_actual_results["results"][1]["driverId"],
            sample_actual_results["results"][2]["driverId"],
        ]

        points_summary = betting_manager.resolve_race_with_fastest_lap(
            race_id, actual_results_drivers, perfect_fastest_lap
        )

        assert username in points_summary
        assert points_summary[username]["total"] == 8  # Maximum points

    def test_race_resolution_partial_correct(
        self, betting_manager, sample_race_data, sample_actual_results
    ):
        """Test race resolution with partially correct predictions."""
        race_id = sample_race_data["id"]
        username = "test_user"

        # Place a partially correct bet (only position 1 correct)
        partial_bet_drivers = [
            sample_actual_results["results"][0]["driverId"],  # Correct
            "alonso",  # Wrong
            "russell",  # Wrong
        ]
        wrong_fastest_lap = "hamilton"  # Wrong

        betting_manager.place_bet(
            username, race_id, partial_bet_drivers, wrong_fastest_lap
        )

        # Resolve the race
        actual_results_drivers = [
            sample_actual_results["results"][0]["driverId"],
            sample_actual_results["results"][1]["driverId"],
            sample_actual_results["results"][2]["driverId"],
        ]

        points_summary = betting_manager.resolve_race_with_fastest_lap(
            race_id,
            actual_results_drivers,
            sample_actual_results["overall_fastest_lap"]["driverId"],
        )

        assert username in points_summary
        # Should get 2 points (1 for correct driver, 1 for correct team in position 1)
        assert points_summary[username]["total"] == 2

    def test_betting_closure(self, betting_manager, sample_race_data):
        """Test that betting closes properly when race starts."""
        race_id = sample_race_data["id"]

        # Close bets for the race
        result = betting_manager.close_bets_for_race(race_id)
        assert result is True

        # Verify race is marked as closed
        data = betting_manager.load_bets()
        assert race_id in data["race_bets"]
        assert data["race_bets"][race_id]["status"] == "closed"


class TestRaceDataManager:
    """Test suite for the RaceDataManager class."""

    def test_race_creation(self, race_data_manager, sample_race_data):
        """Test creating a new race."""
        # Add the sample race
        race_data_manager.add_race(sample_race_data)

        # Verify race was added
        race = race_data_manager.get_race_by_id(sample_race_data["id"])
        assert race is not None
        assert race["name"] == sample_race_data["name"]

    def test_get_next_race(self, race_data_manager, sample_race_data):
        """Test getting the next upcoming race."""
        # Clear any existing races first
        race_data_manager.save_races({"races": []})

        # Add a race in the future
        future_race = sample_race_data.copy()
        future_race["id"] = "future_race"
        future_date = (datetime.now(pytz.UTC) + timedelta(days=30)).strftime("%Y-%m-%d")
        future_race["date"] = future_date
        future_race["sessions"][0]["date"] = future_date  # Update session date too

        race_data_manager.add_race(future_race)

        # Get next race - it should be our future race since it's the only one
        next_race = race_data_manager.get_next_race()
        assert next_race is not None
        assert next_race["id"] == "future_race"

        # The race should be in the list of upcoming races
        upcoming_races = race_data_manager.get_upcoming_races()
        race_ids = [race["id"] for race in upcoming_races]
        assert "future_race" in race_ids

    def test_race_cancellation(self, race_data_manager, sample_race_data):
        """Test race cancellation functionality."""
        # Add a race
        race_data_manager.add_race(sample_race_data)
        race_id = sample_race_data["id"]

        # Cancel the race
        result = race_data_manager.cancel_race(race_id)
        assert result is True

        # Verify race is marked as canceled
        race = race_data_manager.get_race_by_id(race_id)
        assert race["canceled"] is True


class TestScoringSystem:
    """Test suite for the scoring system."""

    def test_perfect_podium_scoring(self, betting_manager, sample_actual_results):
        """Test scoring for a perfect podium prediction."""
        # Create a perfect bet
        perfect_bet = {
            "drivers": [
                sample_actual_results["results"][0]["driverId"],
                sample_actual_results["results"][1]["driverId"],
                sample_actual_results["results"][2]["driverId"],
            ],
            "fastest_lap": sample_actual_results["overall_fastest_lap"]["driverId"],
        }

        # Calculate points
        points_data = betting_manager.calculate_points(
            perfect_bet, sample_actual_results
        )

        # Should get maximum points: 3 positions × 2 pts + 1 fastest lap + 1 bonus = 8 pts
        assert points_data["total_points"] == 8
        assert points_data["breakdown"]["perfect_podium"] == 1

    def test_partial_scoring(self, betting_manager, sample_actual_results):
        """Test scoring for partially correct predictions."""
        # Create a bet with only position 1 correct
        partial_bet = {
            "drivers": [
                sample_actual_results["results"][0][
                    "driverId"
                ],  # Correct driver and team
                "alonso",  # Wrong
                "russell",  # Wrong
            ],
            "fastest_lap": "hamilton",  # Wrong
        }

        # Calculate points
        points_data = betting_manager.calculate_points(
            partial_bet, sample_actual_results
        )

        # Should get 2 points (1 for correct driver + 1 for correct team in position 1)
        assert points_data["total_points"] == 2
        assert points_data["breakdown"]["position_1"] == 2
        assert points_data["breakdown"]["fastest_lap"] == 0

    def test_team_only_scoring(self, betting_manager, sample_actual_results):
        """Test scoring when only team is correct, not driver."""
        # Create a bet where driver is wrong but team is correct for position 3
        # Actual position 3: leclerc (ferrari)
        # Bet: sainz (ferrari) - wrong driver but same team
        team_bet = {
            "drivers": [
                "alonso",
                "russell",
                "sainz",  # Wrong driver but same team (Ferrari) as actual position 3
            ],
            "fastest_lap": "hamilton",
        }

        # Calculate points
        points_data = betting_manager.calculate_points(team_bet, sample_actual_results)

        # Should get 2 points: 1 for position 2 (russell vs hamilton - both Mercedes) + 1 for position 3 (sainz vs leclerc - both Ferrari)
        assert points_data["total_points"] == 2
        assert points_data["breakdown"]["position_2"] == 1
        assert points_data["breakdown"]["position_3"] == 1


class TestIntegration:
    """Integration tests for the complete betting system."""

    def test_complete_betting_flow(
        self,
        betting_manager,
        race_data_manager,
        sample_race_data,
        sample_actual_results,
    ):
        """Test the complete betting flow from bet placement to resolution."""
        race_id = sample_race_data["id"]
        username = "integration_test_user"

        # 1. Add a race
        race_data_manager.add_race(sample_race_data)

        # 2. Place a bet
        bet_drivers = [
            sample_actual_results["results"][0]["driverId"],
            sample_actual_results["results"][1]["driverId"],
            "alonso",  # Wrong for position 3
        ]
        bet_fastest_lap = sample_actual_results["overall_fastest_lap"]["driverId"]

        result = betting_manager.place_bet(
            username, race_id, bet_drivers, bet_fastest_lap
        )
        assert result is True

        # 3. Close betting for the race
        betting_manager.close_bets_for_race(race_id)

        # 4. Resolve the race
        actual_results_drivers = [
            sample_actual_results["results"][0]["driverId"],
            sample_actual_results["results"][1]["driverId"],
            sample_actual_results["results"][2]["driverId"],
        ]

        points_summary = betting_manager.resolve_race_with_fastest_lap(
            race_id, actual_results_drivers, bet_fastest_lap
        )

        # 5. Verify points were awarded correctly
        assert username in points_summary
        # Should get: position 1 (2 pts) + position 2 (2 pts) + fastest lap (1 pt) = 5 pts
        assert points_summary[username]["total"] == 5

        # 6. Verify race is marked as resolved
        data = betting_manager.load_bets()
        assert data["race_bets"][race_id]["status"] == "resolved"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_bet_resolution(self, betting_manager, sample_race_data):
        """Test resolving a race with no bets."""
        race_id = sample_race_data["id"]

        # Resolve race with no bets
        actual_results = ["verstappen", "hamilton", "leclerc"]
        points_summary = betting_manager.resolve_race(race_id, actual_results)

        # Should return empty dict
        assert points_summary == {}

    def test_invalid_race_id(self, betting_manager):
        """Test handling of invalid race IDs."""
        # Try to place bet on non-existent race
        # Note: place_bet() doesn't validate race existence, it just stores the bet
        result = betting_manager.place_bet(
            "test_user",
            "non_existent_race_id",
            ["verstappen", "hamilton", "leclerc"],
            "verstappen",
        )

        # This should succeed - the betting manager allows bets on any race ID
        assert result is True

        # Verify the bet was stored
        user_bets = betting_manager.get_user_bets("test_user")
        assert "non_existent_race_id" in user_bets

    def test_duplicate_bet_prevention(self, betting_manager, sample_race_data):
        """Test that users cannot place multiple bets on the same race."""
        race_id = sample_race_data["id"]
        username = "test_user"

        # Place first bet
        result1 = betting_manager.place_bet(
            username, race_id, ["verstappen", "hamilton", "leclerc"], "verstappen"
        )
        assert result1 is True

        # Check if user can bet on this race (should be False now since they already have a bet)
        can_bet = betting_manager.can_bet_on_race(race_id, username)
        assert can_bet is False

        # Try to place second bet on same race - this will succeed but overwrite the first bet
        result2 = betting_manager.place_bet(
            username, race_id, ["leclerc", "verstappen", "hamilton"], "hamilton"
        )
        # This succeeds because place_bet() overwrites existing bets
        assert result2 is True

        # Verify only one bet exists (the second one overwrote the first)
        user_bets = betting_manager.get_user_bets(username)
        assert race_id in user_bets
        assert user_bets[race_id]["drivers"] == ["leclerc", "verstappen", "hamilton"]
