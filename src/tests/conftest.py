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
from app.race_data_manager import RaceDataManager


@pytest.fixture(scope="session", autouse=True)
def isolated_data_files(tmp_path_factory):
    """Redirect all singleton JsonStores to temp files so tests never touch real data."""
    import tempfile, os
    from app.core import JsonStore
    from app.services import bet_service, user_service, resolution_service
    from app.push_manager import push_manager

    tmp = tmp_path_factory.mktemp("test_data")
    bet_service._store = JsonStore(str(tmp / "bets.json"), default={"race_bets": {}, "metadata": {}})
    user_service._store = JsonStore(str(tmp / "users.json"), default={"users": {}})
    resolution_service._cache = JsonStore(str(tmp / "race_results.json"), default={})
    push_manager._store = JsonStore(str(tmp / "push_subscriptions.json"), default={"subscriptions": {}})
    yield


@pytest.fixture(scope="session")
def app():
    """Create and configure a new app instance for each test."""
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False

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
def bet_service(app):
    """Provide the bet service with isolated data for each test."""
    from app.services import bet_service as svc, resolution_service
    with app.app_context():
        svc.save_all({"race_bets": {}, "metadata": {}})
        resolution_service.set_driver_teams({
            "verstappen": "red_bull",
            "hamilton": "mercedes",
            "leclerc": "ferrari",
            "alonso": "aston_martin",
            "russell": "mercedes",
            "sainz": "ferrari",
        })
        yield svc
        svc.save_all({"race_bets": {}, "metadata": {}})


@pytest.fixture(scope="function")
def race_data_manager(app):
    """Provide a race data manager instance for testing."""
    with app.app_context():
        test_data_file = "/tmp/test_races.json"
        manager = RaceDataManager(data_file=test_data_file)

        yield manager

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
