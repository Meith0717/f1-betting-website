"""
Pure scoring engine for F1 race predictions.

Scoring rules (max 8 points per race):
  - +1 per correct driver in the correct podium position
  - +1 per correct team in the correct podium position
  - +1 for correct fastest lap prediction
  - +1 bonus for perfect podium (all 3 drivers AND teams correct)
"""

from typing import Dict, List, Optional


class ScoringEngine:
    """Calculates points for user bets against actual race results."""

    def __init__(self, driver_teams: Dict[str, str]):
        """
        Args:
            driver_teams: Mapping of driver_id -> team_id
        """
        self.driver_teams = driver_teams

    def calculate(
        self, user_bet: Dict, actual_results: Dict
    ) -> Dict:
        """
        Calculate points for a single user bet.

        Args:
            user_bet: {"drivers": [driver_id, ...], "fastest_lap": driver_id}
            actual_results: {"results": [{"driverId": ..., "teamId": ...}, ...],
                              "overall_fastest_lap": {"driverId": ...}}

        Returns:
            {"total_points": int, "breakdown": {"position_1": int, ...}}
        """
        points = 0
        breakdown = {
            "position_1": 0,
            "position_2": 0,
            "position_3": 0,
            "fastest_lap": 0,
            "perfect_podium": 0,
        }

        actual_positions: List[Optional[str]] = []
        actual_teams: List[Optional[str]] = []
        for result in actual_results.get("results", [])[:3]:
            actual_positions.append(result.get("driverId"))
            actual_teams.append(result.get("teamId"))

        actual_fastest_lap = (
            actual_results.get("overall_fastest_lap", {}).get("driverId")
        )

        perfect_podium = True
        bet_drivers = user_bet.get("drivers", [])

        for i in range(3):
            if i >= len(bet_drivers):
                continue

            bet_driver = bet_drivers[i]
            if i >= len(actual_positions):
                perfect_podium = False
                continue

            actual_driver = actual_positions[i]
            actual_team = actual_teams[i]
            bet_team = self.driver_teams.get(bet_driver)

            if bet_driver == actual_driver:
                points += 1
                breakdown[f"position_{i + 1}"] += 1

            if bet_team is not None and bet_team == actual_team:
                points += 1
                breakdown[f"position_{i + 1}"] += 1

            if bet_driver != actual_driver or bet_team != actual_team:
                perfect_podium = False

        if user_bet.get("fastest_lap") and user_bet["fastest_lap"] == actual_fastest_lap:
            points += 1
            breakdown["fastest_lap"] = 1

        if perfect_podium and len(bet_drivers) >= 3:
            points += 1
            breakdown["perfect_podium"] = 1

        return {"total_points": points, "breakdown": breakdown}

    @staticmethod
    def build_actual_results(
        top3_drivers: List[str],
        driver_teams: Dict[str, str],
        fastest_lap_driver: Optional[str] = None,
    ) -> Dict:
        """
        Build the actual_results dict expected by calculate() from raw driver IDs.

        Args:
            top3_drivers: List of 3 driver IDs in finishing order
            driver_teams: Mapping of driver_id -> team_id
            fastest_lap_driver: Optional driver ID for fastest lap

        Returns:
            Dict in the format expected by calculate()
        """
        results = {
            "results": [
                {
                    "driverId": d,
                    "teamId": driver_teams.get(d),
                }
                for d in top3_drivers
            ]
        }
        if fastest_lap_driver:
            results["overall_fastest_lap"] = {
                "driverId": fastest_lap_driver,
                "teamId": driver_teams.get(fastest_lap_driver),
            }
        return results
