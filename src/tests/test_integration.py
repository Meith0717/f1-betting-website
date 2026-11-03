#!/usr/bin/env python3
"""
Integration test for the F1 Betting scoring system.
Tests the ScoringEngine with actual data files and real-world scenarios.
"""

import sys
import os
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.scoring import ScoringEngine


def test_with_real_data():
    """Test the scoring system with real data files."""
    data_dir = os.path.join(os.path.dirname(__file__), "..", "app", "data")

    drivers_file = os.path.join(data_dir, "drivers.json")
    race_results_file = os.path.join(data_dir, "race_results.json")

    if not os.path.exists(drivers_file) or not os.path.exists(race_results_file):
        pytest.skip("Data files not found — run update-drivers / update-races first")

    with open(drivers_file, "r") as f:
        driver_data = json.load(f)
    with open(race_results_file, "r") as f:
        race_results_data = json.load(f)

    driver_teams = {}
    for driver in driver_data.get("drivers", []):
        driver_id = driver.get("driverId")
        team_id = driver.get("teamId")
        if driver_id and team_id:
            driver_teams[driver_id] = team_id

    if not driver_teams or not race_results_data:
        pytest.skip("Data files are empty — run update-drivers / update-races first")

    engine = ScoringEngine(driver_teams)

    test_race_id = list(race_results_data.keys())[0]
    test_results = race_results_data[test_race_id]

    # Build actual results from real data
    actual = ScoringEngine.build_actual_results(
        [r["driverId"] for r in test_results["results"][:3]],
        driver_teams,
        test_results.get("overall_fastest_lap", {}).get("driverId"),
    )

    # Perfect podium test
    perfect_bet = {
        "drivers": [r["driverId"] for r in test_results["results"][:3]],
        "fastest_lap": test_results["overall_fastest_lap"]["driverId"],
    }
    result = engine.calculate(perfect_bet, actual)
    assert result["total_points"] == 8, f"Perfect podium should give 8 pts, got {result['total_points']}"

    # Edge case: empty bet
    empty_bet = {"drivers": [], "fastest_lap": "ver"}
    result = engine.calculate(empty_bet, actual)
    assert result["total_points"] >= 0

    # Edge case: missing fastest lap in bet
    no_fl_bet = {"drivers": [r["driverId"] for r in test_results["results"][:3]], "fastest_lap": None}
    result = engine.calculate(no_fl_bet, actual)
    assert result["total_points"] == 7  # 6 for podium + 1 bonus, no FL point


if __name__ == "__main__":
    test_with_real_data()
    print("Integration test passed!")
