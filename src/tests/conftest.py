"""
Pytest configuration and fixtures for F1 Betting application tests.
"""

import pytest
import sys
import os
from datetime import datetime, timedelta
import pytz

# Add src directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.betting_manager import BettingManager
from app.race_data_manager import RaceDataManager


@pytest.fixture(scope="session")
def app():
    """Create and configure a new app instance for each test."""
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False  # Disable CSRF for testing

    # Set up application context
    with app.app_context():
        yield app


@pytest.fixture(scope="session")
def client(app):
    """Create a test client for the app."""
    return app.test_client()


@pytest.fixture(scope="session")
def runner(app):
    """Create a test runner for the app."""
    return app.test_cli_runner()


@pytest.fixture(scope="function")
def betting_manager(app):
    """Provide a betting manager instance for testing."""
    with app.app_context():
        # Create a test betting manager with isolated data
        test_data_file = "/tmp/test_bets.json"
        manager = BettingManager(data_file=test_data_file)

        # Set up test driver teams
        manager.driver_teams = {
            "verstappen": "red_bull",
            "hamilton": "mercedes",
            "leclerc": "ferrari",
            "alonso": "aston_martin",
            "russell": "mercedes",
            "sainz": "ferrari",
        }

        yield manager

        # Clean up
        if os.path.exists(test_data_file):
            os.remove(test_data_file)


@pytest.fixture(scope="function")
def race_data_manager(app):
    """Provide a race data manager instance for testing."""
    with app.app_context():
        # Create a test race data manager with isolated data
        test_data_file = "/tmp/test_races.json"
        manager = RaceDataManager(data_file=test_data_file)

        yield manager

        # Clean up
        if os.path.exists(test_data_file):
            os.remove(test_data_file)


@pytest.fixture
def sample_race_data():
    """Provide sample race data for testing."""
    return {
        "id": "test_race_2024",
        "name": "Test Grand Prix",
        "country": "Testland",
        "circuit": "Test Circuit",
        "date": "2024-03-30",
        "time": "14:00:00",
        "sessions": [{"type": "Race", "date": "2024-03-30", "time": "14:00:00"}],
    }


@pytest.fixture
def sample_user_bet():
    """Provide sample user bet data for testing."""
    return {
        "drivers": ["verstappen", "hamilton", "leclerc"],
        "fastest_lap": "verstappen",
        "created_at": datetime.now(pytz.UTC).isoformat(),
    }


@pytest.fixture
def sample_actual_results():
    """Provide sample actual race results for testing."""
    return {
        "results": [
            {"driverId": "verstappen", "teamId": "red_bull"},
            {"driverId": "hamilton", "teamId": "mercedes"},
            {"driverId": "leclerc", "teamId": "ferrari"},
        ],
        "overall_fastest_lap": {"driverId": "verstappen", "teamId": "red_bull"},
    }


@pytest.fixture
def test_client_with_session(client):
    """Create a test client with session support."""
    with client.session_transaction() as sess:
        sess["username"] = "test_user"
        sess["is_admin"] = False
    return client
