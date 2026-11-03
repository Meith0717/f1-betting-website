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


class TestBetService:
    """Test suite for the BetService class."""

    def test_bet_placement_valid(
        self, bet_service, sample_race_data, sample_user_bet
    ):
        """Test placing a valid bet."""
        race_id = sample_race_data["id"]
        username = "test_user"

        result = bet_service.place_bet(
            username,
            race_id,
            sample_user_bet["drivers"],
            sample_user_bet["fastest_lap"],
        )

        assert result is True

        user_bets = bet_service.get_user_bets(username)
        assert race_id in user_bets
        assert user_bets[race_id]["drivers"] == sample_user_bet["drivers"]
        assert user_bets[race_id]["fastest_lap"] == sample_user_bet["fastest_lap"]

    def test_bet_placement_invalid_duplicate_drivers(
        self, bet_service, sample_race_data
    ):
        """Test that bets with duplicate drivers are rejected."""
        race_id = sample_race_data["id"]
        username = "test_user"

        result = bet_service.place_bet(
            username,
            race_id,
            ["verstappen", "verstappen", "hamilton"],
            "verstappen",
        )

        assert result is False

    def test_bet_placement_invalid_wrong_count(self, bet_service, sample_race_data):
        """Test that bets with wrong number of drivers are rejected."""
        race_id = sample_race_data["id"]
        username = "test_user"

        result = bet_service.place_bet(
            username,
            race_id,
            ["verstappen", "hamilton"],
            "verstappen",
        )

        assert result is False

    def test_race_resolution_perfect_podium(
        self, bet_service, sample_race_data, sample_actual_results
    ):
        """Test race resolution with perfect podium prediction."""
        from app.services import resolution_service

        race_id = sample_race_data["id"]
        username = "test_user"

        perfect_bet_drivers = [
            sample_actual_results["results"][0]["driverId"],
            sample_actual_results["results"][1]["driverId"],
            sample_actual_results["results"][2]["driverId"],
        ]
        perfect_fastest_lap = sample_actual_results["overall_fastest_lap"]["driverId"]

        bet_service.place_bet(
            username, race_id, perfect_bet_drivers, perfect_fastest_lap
        )

        actual_results_drivers = [
            sample_actual_results["results"][0]["driverId"],
            sample_actual_results["results"][1]["driverId"],
            sample_actual_results["results"][2]["driverId"],
        ]

        summary = resolution_service.resolve_with_results(
            race_id, actual_results_drivers, perfect_fastest_lap
        )

        assert username in summary
        assert summary[username]["total_points"] == 8

    def test_race_resolution_partial_correct(
        self, bet_service, sample_race_data, sample_actual_results
    ):
        """Test race resolution with partially correct predictions."""
        from app.services import resolution_service

        race_id = sample_race_data["id"]
        username = "test_user"

        partial_bet_drivers = [
            sample_actual_results["results"][0]["driverId"],
            "alonso",
            "russell",
        ]
        wrong_fastest_lap = "hamilton"

        bet_service.place_bet(
            username, race_id, partial_bet_drivers, wrong_fastest_lap
        )

        actual_results_drivers = [
            sample_actual_results["results"][0]["driverId"],
            sample_actual_results["results"][1]["driverId"],
            sample_actual_results["results"][2]["driverId"],
        ]

        summary = resolution_service.resolve_with_results(
            race_id,
            actual_results_drivers,
            sample_actual_results["overall_fastest_lap"]["driverId"],
        )

        assert username in summary
        assert summary[username]["total_points"] == 2

    def test_betting_closure(self, bet_service, sample_race_data):
        """Test that betting closes properly when race starts."""
        race_id = sample_race_data["id"]

        result = bet_service.close_race(race_id)
        assert result is True

        data = bet_service.load_all()
        assert race_id in data["race_bets"]
        assert data["race_bets"][race_id]["status"] == "closed"


class TestRaceDataManager:
    """Test suite for the RaceDataManager class."""

    def test_race_creation(self, race_data_manager, sample_race_data):
        """Test creating a new race."""
        race_data_manager.add_race(sample_race_data)

        race = race_data_manager.get_race_by_id(sample_race_data["id"])
        assert race is not None
        assert race["name"] == sample_race_data["name"]

    def test_get_next_race(self, race_data_manager, sample_race_data):
        """Test getting the next upcoming race."""
        race_data_manager.save_races({"races": []})

        future_race = sample_race_data.copy()
        future_race["id"] = "future_race"
        future_date = (datetime.now(pytz.UTC) + timedelta(days=30)).strftime("%Y-%m-%d")
        future_race["date"] = future_date
        future_race["sessions"][0]["date"] = future_date

        race_data_manager.add_race(future_race)

        next_race = race_data_manager.get_next_race()
        assert next_race is not None
        assert next_race["id"] == "future_race"

        upcoming_races = race_data_manager.get_upcoming_races()
        race_ids = [race["id"] for race in upcoming_races]
        assert "future_race" in race_ids

    def test_race_cancellation(self, race_data_manager, sample_race_data):
        """Test race cancellation functionality."""
        race_data_manager.add_race(sample_race_data)
        race_id = sample_race_data["id"]

        result = race_data_manager.cancel_race(race_id)
        assert result is True

        race = race_data_manager.get_race_by_id(race_id)
        assert race["canceled"] is True


class TestScoringSystem:
    """Test suite for the scoring system via ResolutionService."""

    def test_perfect_podium_scoring(self, bet_service, sample_actual_results):
        """Test scoring for a perfect podium prediction."""
        from app.services import resolution_service

        perfect_bet = {
            "drivers": [
                sample_actual_results["results"][0]["driverId"],
                sample_actual_results["results"][1]["driverId"],
                sample_actual_results["results"][2]["driverId"],
            ],
            "fastest_lap": sample_actual_results["overall_fastest_lap"]["driverId"],
        }

        result = resolution_service._scoring.calculate(perfect_bet, sample_actual_results)

        assert result["total_points"] == 8
        assert result["breakdown"]["perfect_podium"] == 1

    def test_partial_scoring(self, bet_service, sample_actual_results):
        """Test scoring for partially correct predictions."""
        from app.services import resolution_service

        partial_bet = {
            "drivers": [
                sample_actual_results["results"][0]["driverId"],
                "alonso",
                "russell",
            ],
            "fastest_lap": "hamilton",
        }

        result = resolution_service._scoring.calculate(partial_bet, sample_actual_results)

        assert result["total_points"] == 2
        assert result["breakdown"]["position_1"] == 2
        assert result["breakdown"]["fastest_lap"] == 0

    def test_team_only_scoring(self, bet_service, sample_actual_results):
        """Test scoring when only team is correct, not driver."""
        from app.services import resolution_service

        team_bet = {
            "drivers": [
                "alonso",
                "russell",
                "sainz",
            ],
            "fastest_lap": "hamilton",
        }

        result = resolution_service._scoring.calculate(team_bet, sample_actual_results)

        assert result["total_points"] == 2
        assert result["breakdown"]["position_2"] == 1
        assert result["breakdown"]["position_3"] == 1


class TestIntegration:
    """Integration tests for the complete betting system."""

    def test_complete_betting_flow(
        self,
        bet_service,
        race_data_manager,
        sample_race_data,
        sample_actual_results,
    ):
        """Test the complete betting flow from bet placement to resolution."""
        from app.services import resolution_service

        race_id = sample_race_data["id"]
        username = "integration_test_user"

        race_data_manager.add_race(sample_race_data)

        bet_drivers = [
            sample_actual_results["results"][0]["driverId"],
            sample_actual_results["results"][1]["driverId"],
            "alonso",
        ]
        bet_fastest_lap = sample_actual_results["overall_fastest_lap"]["driverId"]

        result = bet_service.place_bet(
            username, race_id, bet_drivers, bet_fastest_lap
        )
        assert result is True

        bet_service.close_race(race_id)

        actual_results_drivers = [
            sample_actual_results["results"][0]["driverId"],
            sample_actual_results["results"][1]["driverId"],
            sample_actual_results["results"][2]["driverId"],
        ]

        summary = resolution_service.resolve_with_results(
            race_id, actual_results_drivers, bet_fastest_lap
        )

        assert username in summary
        assert summary[username]["total_points"] == 5

        data = bet_service.load_all()
        assert data["race_bets"][race_id]["status"] == "resolved"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_bet_resolution(self, bet_service, sample_race_data):
        """Test resolving a race with no bets."""
        from app.services import resolution_service

        race_id = sample_race_data["id"]
        summary = resolution_service.resolve_with_results(
            race_id, ["verstappen", "hamilton", "leclerc"]
        )
        assert summary == {}

    def test_invalid_race_id(self, bet_service):
        """Test handling of invalid race IDs."""
        result = bet_service.place_bet(
            "test_user",
            "non_existent_race_id",
            ["verstappen", "hamilton", "leclerc"],
            "verstappen",
        )
        assert result is True

        user_bets = bet_service.get_user_bets("test_user")
        assert "non_existent_race_id" in user_bets

    def test_duplicate_bet_prevention(self, bet_service, sample_race_data):
        """Test that users cannot place multiple bets on the same race."""
        race_id = sample_race_data["id"]
        username = "test_user"

        result1 = bet_service.place_bet(
            username, race_id, ["verstappen", "hamilton", "leclerc"], "verstappen"
        )
        assert result1 is True

        can_bet = bet_service.can_bet_on_race(race_id, username)
        assert can_bet is False

        result2 = bet_service.place_bet(
            username, race_id, ["leclerc", "verstappen", "hamilton"], "hamilton"
        )
        assert result2 is True

        user_bets = bet_service.get_user_bets(username)
        assert race_id in user_bets
        assert user_bets[race_id]["drivers"] == ["leclerc", "verstappen", "hamilton"]
