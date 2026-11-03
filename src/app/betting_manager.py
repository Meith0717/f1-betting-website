"""
BettingManager — thin facade over the service layer.

This preserves the public API used by routes and templates while delegating
all actual work to focused services:
  - BetService (services/bet_service.py)     — bet CRUD, eligibility, closure
  - ResolutionService (services/resolution_service.py) — scoring, API, resolution
  - UserService (services/user_service.py)   — score updates
  - ScoringEngine (core/scoring.py)          — pure points calculation
"""

import os
from typing import Dict, List, Optional

from .core.logger import get_logger
from .services import bet_service, resolution_service, user_service


class BettingManager:
    """Facade combining bet, scoring, and resolution operations."""

    def __init__(self):
        self._logger = get_logger(__name__)
        # Wire up dependencies (race_manager injected after it's available)
        from .race_data_manager import race_data_manager

        bet_service.set_race_manager(race_data_manager)
        resolution_service.set_dependencies(
            bet_service, user_service, race_data_manager
        )

    # -- Pass-through: bet operations ---------------------------------------

    def load_bets(self) -> Dict:
        return bet_service.load_all()

    def save_bets(self, data: Dict):
        bet_service.save_all(data)

    def get_all_bets(self) -> Dict:
        return bet_service.load_all()

    def get_user_bets(self, username: str) -> Dict:
        return bet_service.get_user_bets(username)

    def get_race_bets(self, race_id: str) -> Dict:
        return bet_service.get_race_bets(race_id)

    def place_bet(self, username: str, race_id: str, bets: List[str], fastest_lap: str = None) -> bool:
        return bet_service.place_bet(username, race_id, bets, fastest_lap)

    def can_bet_on_race(self, race_id: str, username: str = None) -> bool:
        return bet_service.can_bet_on_race(race_id, username)

    def is_betting_closed(self, race_id: str) -> bool:
        return bet_service.is_betting_closed(race_id)

    def close_bets_for_race(self, race_id: str, data: Dict = None) -> bool:
        return bet_service.close_race(race_id, data)

    def check_and_close_expired_bets(self) -> int:
        return bet_service.check_and_close_expired()

    def get_available_drivers_for_race(self, race_id: str) -> List[Dict]:
        return bet_service.get_available_drivers()

    # -- Pass-through: scoring & resolution ---------------------------------

    @property
    def driver_teams(self) -> Dict[str, str]:
        if resolution_service._scoring:
            return resolution_service._scoring.driver_teams
        return {}

    def calculate_points(self, user_bet: Dict, actual_results: Dict) -> Dict:
        if not resolution_service._scoring:
            resolution_service.refresh_driver_teams()
        return resolution_service._scoring.calculate(user_bet, actual_results)

    @staticmethod
    def _format_summary(summary: Dict) -> Dict:
        """Convert {user: {total_points, breakdown}} to legacy {user: {total, breakdown}}."""
        return {
            user: {"total": r["total_points"], "breakdown": r["breakdown"]}
            for user, r in summary.items()
        }

    def resolve_race(self, race_id: str, actual_results: List[str]) -> Dict:
        return self._format_summary(
            resolution_service.resolve_with_results(race_id, actual_results)
        )

    def resolve_race_with_fastest_lap(
        self, race_id: str, actual_results: List[str], fastest_lap_driver: str = None
    ) -> Dict:
        return self._format_summary(
            resolution_service.resolve_with_results(
                race_id, actual_results, fastest_lap_driver
            )
        )

    def resolve_race_from_api(self, race_id: str) -> bool:
        return resolution_service.resolve_from_api(race_id)

    def get_race_results(self, race_id: str) -> Optional[Dict]:
        return resolution_service.get_results(race_id)

    def update_user_score(self, username: str, points: int, race_id: str) -> bool:
        return user_service.add_score(username, points, race_id)


betting_manager = BettingManager()
