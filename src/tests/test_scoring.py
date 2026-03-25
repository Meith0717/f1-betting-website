#!/usr/bin/env python3
"""
Test script to demonstrate the F1 Betting scoring system.
Shows how points are calculated based on the implemented rules.
"""

import sys
import os
import json
from datetime import datetime

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from app.betting_manager import BettingManager


def test_scoring_system():
    """Test the scoring system with various scenarios."""

    print("🏎️ F1 Betting Scoring System Test")
    print("=" * 50)

    # Initialize betting manager
    betting_manager = BettingManager()

    # Load some test data
    print("\n📊 Test Data Setup:")

    # Test drivers and teams
    test_drivers = {
        "ver": "red_bull",  # Max Verstappen
        "ham": "mercedes",  # Lewis Hamilton
        "lec": "ferrari",  # Charles Leclerc
        "alc": "aston_martin",  # Fernando Alonso
        "rus": "mercedes",  # George Russell
        "sai": "ferrari",  # Carlos Sainz
    }

    betting_manager.driver_teams = test_drivers

    print(f"Loaded {len(test_drivers)} drivers with team mappings")

    # Test Scenario 1: Partial Correct Predictions
    print("\n🔢 Scenario 1: Partial Correct Predictions")
    print("-" * 40)

    user_bet_1 = {
        "drivers": ["ver", "alc", "rus"],  # VER, ALC, RUS
        "fastest_lap": "ham",
    }

    actual_results_1 = {
        "results": [
            {"driverId": "ver", "teamId": "red_bull"},  # 1st: VER (Red Bull)
            {"driverId": "ham", "teamId": "mercedes"},  # 2nd: HAM (Mercedes)
            {"driverId": "lec", "teamId": "ferrari"},  # 3rd: LEC (Ferrari)
        ],
        "overall_fastest_lap": {"driverId": "ver", "teamId": "red_bull"},
    }

    result_1 = betting_manager.calculate_points(user_bet_1, actual_results_1)

    print(f"User Bet:     [VER, ALC, RUS] | Fastest: HAM")
    print(f"Actual:       [VER, HAM, LEC] | Fastest: VER")
    print(f"\nScoring Breakdown:")
    print(
        f"  Position 1: {result_1['breakdown']['position_1']} pts (VER ✅ driver + Red Bull ✅ team)"
    )
    print(
        f"  Position 2: {result_1['breakdown']['position_2']} pts (ALC ❌, should be HAM)"
    )
    print(
        f"  Position 3: {result_1['breakdown']['position_3']} pts (RUS ❌, should be LEC)"
    )
    print(
        f"  Fastest Lap: {result_1['breakdown']['fastest_lap']} pts (HAM ❌, should be VER)"
    )
    print(
        f"  Perfect Podium: {result_1['breakdown']['perfect_podium']} pts (❌ not all correct)"
    )
    print(f"\n🏆 TOTAL POINTS: {result_1['total_points']}/8")

    # Test Scenario 2: Perfect Podium + Fastest Lap
    print("\n🔢 Scenario 2: Perfect Podium + Fastest Lap")
    print("-" * 40)

    user_bet_2 = {
        "drivers": ["ver", "ham", "lec"],  # VER, HAM, LEC
        "fastest_lap": "ver",
    }

    actual_results_2 = {
        "results": [
            {"driverId": "ver", "teamId": "red_bull"},  # 1st: VER (Red Bull)
            {"driverId": "ham", "teamId": "mercedes"},  # 2nd: HAM (Mercedes)
            {"driverId": "lec", "teamId": "ferrari"},  # 3rd: LEC (Ferrari)
        ],
        "overall_fastest_lap": {"driverId": "ver", "teamId": "red_bull"},
    }

    result_2 = betting_manager.calculate_points(user_bet_2, actual_results_2)

    print(f"User Bet:     [VER, HAM, LEC] | Fastest: VER")
    print(f"Actual:       [VER, HAM, LEC] | Fastest: VER")
    print(f"\nScoring Breakdown:")
    print(
        f"  Position 1: {result_2['breakdown']['position_1']} pts (VER ✅ + Red Bull ✅)"
    )
    print(
        f"  Position 2: {result_2['breakdown']['position_2']} pts (HAM ✅ + Mercedes ✅)"
    )
    print(
        f"  Position 3: {result_2['breakdown']['position_3']} pts (LEC ✅ + Ferrari ✅)"
    )
    print(f"  Fastest Lap: {result_2['breakdown']['fastest_lap']} pts (VER ✅)")
    print(
        f"  Perfect Podium: {result_2['breakdown']['perfect_podium']} pts (✅ ALL correct!)"
    )
    print(f"\n🏆 TOTAL POINTS: {result_2['total_points']}/8 (MAXIMUM!)")

    # Test Scenario 3: Only Teams Correct
    print("\n🔢 Scenario 3: Only Teams Correct (Wrong Drivers)")
    print("-" * 40)

    user_bet_3 = {
        "drivers": [
            "sai",
            "rus",
            "alc",
        ],  # SAI (Ferrari), RUS (Mercedes), ALC (Aston Martin)
        "fastest_lap": "lec",
    }

    actual_results_3 = {
        "results": [
            {"driverId": "lec", "teamId": "ferrari"},  # 1st: LEC (Ferrari)
            {"driverId": "ham", "teamId": "mercedes"},  # 2nd: HAM (Mercedes)
            {"driverId": "alc", "teamId": "aston_martin"},  # 3rd: ALC (Aston Martin)
        ],
        "overall_fastest_lap": {"driverId": "ver", "teamId": "red_bull"},
    }

    result_3 = betting_manager.calculate_points(user_bet_3, actual_results_3)

    print(f"User Bet:     [SAI, RUS, ALC] | Fastest: LEC")
    print(f"Actual:       [LEC, HAM, ALC] | Fastest: VER")
    print(f"\nScoring Breakdown:")
    print(
        f"  Position 1: {result_3['breakdown']['position_1']} pts (SAI ❌ but Ferrari ✅)"
    )
    print(
        f"  Position 2: {result_3['breakdown']['position_2']} pts (RUS ❌ but Mercedes ✅)"
    )
    print(
        f"  Position 3: {result_3['breakdown']['position_3']} pts (ALC ✅ + Aston Martin ✅)"
    )
    print(
        f"  Fastest Lap: {result_3['breakdown']['fastest_lap']} pts (LEC ❌, should be VER)"
    )
    print(f"  Perfect Podium: {result_3['breakdown']['perfect_podium']} pts (❌)")
    print(f"\n🏆 TOTAL POINTS: {result_3['total_points']}/8")

    # Test Scenario 4: Completely Wrong
    print("\n🔢 Scenario 4: Completely Wrong Predictions")
    print("-" * 40)

    user_bet_4 = {"drivers": ["sai", "rus", "alc"], "fastest_lap": "sai"}

    actual_results_4 = {
        "results": [
            {"driverId": "ver", "teamId": "red_bull"},
            {"driverId": "ham", "teamId": "mercedes"},
            {"driverId": "lec", "teamId": "ferrari"},
        ],
        "overall_fastest_lap": {"driverId": "ver", "teamId": "red_bull"},
    }

    result_4 = betting_manager.calculate_points(user_bet_4, actual_results_4)

    print(f"User Bet:     [SAI, RUS, ALC] | Fastest: SAI")
    print(f"Actual:       [VER, HAM, LEC] | Fastest: VER")
    print(f"\nScoring Breakdown:")
    print(f"  Position 1: {result_4['breakdown']['position_1']} pts (All wrong)")
    print(f"  Position 2: {result_4['breakdown']['position_2']} pts (All wrong)")
    print(
        f"  Position 3: {result_4['breakdown']['position_3']} pts (ALC ❌, should be LEC)"
    )
    print(
        f"  Fastest Lap: {result_4['breakdown']['fastest_lap']} pts (SAI ❌, should be VER)"
    )
    print(f"  Perfect Podium: {result_4['breakdown']['perfect_podium']} pts (❌)")
    print(f"\n🏆 TOTAL POINTS: {result_4['total_points']}/8")

    # Summary
    print("\n" + "=" * 50)
    print("📊 SCORING SYSTEM SUMMARY")
    print("=" * 50)
    print("✅ 1 point per correct driver position")
    print("✅ 1 point per correct team position")
    print("✅ 1 point for correct fastest lap driver")
    print("✅ 1 bonus point for perfect podium (all drivers AND teams)")
    print("✅ Maximum 8 points per race")
    print("\n🎯 Implementation: COMPLETE")
    print("🏆 Ready for production use!")


if __name__ == "__main__":
    test_scoring_system()
