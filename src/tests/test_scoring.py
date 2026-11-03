#!/usr/bin/env python3
"""
Test the F1 Betting scoring system using ScoringEngine directly.
Shows how points are calculated based on the implemented rules.
"""

from app.core.scoring import ScoringEngine


def test_scoring_system():
    """Test the scoring system with various scenarios."""
    test_drivers = {
        "ver": "red_bull",
        "ham": "mercedes",
        "lec": "ferrari",
        "alc": "aston_martin",
        "rus": "mercedes",
        "sai": "ferrari",
    }
    engine = ScoringEngine(test_drivers)

    # Scenario 1: Partial Correct Predictions
    user_bet_1 = {"drivers": ["ver", "alc", "rus"], "fastest_lap": "ham"}
    actual_1 = ScoringEngine.build_actual_results(
        ["ver", "ham", "lec"], test_drivers, "ver"
    )
    result_1 = engine.calculate(user_bet_1, actual_1)
    assert result_1["total_points"] == 2  # pos1: driver+team = 2
    assert result_1["breakdown"]["position_1"] == 2

    # Scenario 2: Perfect Podium + Fastest Lap
    user_bet_2 = {"drivers": ["ver", "ham", "lec"], "fastest_lap": "ver"}
    actual_2 = ScoringEngine.build_actual_results(
        ["ver", "ham", "lec"], test_drivers, "ver"
    )
    result_2 = engine.calculate(user_bet_2, actual_2)
    assert result_2["total_points"] == 8  # maximum
    assert result_2["breakdown"]["perfect_podium"] == 1

    # Scenario 3: Only Teams Correct
    user_bet_3 = {"drivers": ["sai", "rus", "alc"], "fastest_lap": "lec"}
    actual_3 = ScoringEngine.build_actual_results(
        ["lec", "ham", "alc"], test_drivers, "ver"
    )
    result_3 = engine.calculate(user_bet_3, actual_3)
    # pos1: sai(ferrari) vs lec(ferrari) -> team match = 1
    # pos2: rus(mercedes) vs ham(mercedes) -> team match = 1
    # pos3: alc(aston_martin) vs alc(aston_martin) -> driver+team = 2
    assert result_3["total_points"] == 4
    assert result_3["breakdown"]["position_1"] == 1
    assert result_3["breakdown"]["position_2"] == 1
    assert result_3["breakdown"]["position_3"] == 2

    # Scenario 4: Completely Wrong
    user_bet_4 = {"drivers": ["sai", "rus", "alc"], "fastest_lap": "sai"}
    actual_4 = ScoringEngine.build_actual_results(
        ["ver", "ham", "lec"], test_drivers, "ver"
    )
    result_4 = engine.calculate(user_bet_4, actual_4)
    # pos2: rus(mercedes) vs ham(mercedes) -> team match = 1
    assert result_4["total_points"] == 1


if __name__ == "__main__":
    test_scoring_system()
    print("All scoring tests passed!")
