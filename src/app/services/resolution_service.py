"""
Race resolution service.

Handles resolving races (manual entry or F1 API fetch), calculating points
via the ScoringEngine, and updating user scores. Extracted from the
monolithic BettingManager.resolve_* methods.
"""

import json
import os
from typing import Dict, List, Optional

from ..core import JsonStore
from ..core.logger import get_logger
from ..core.scoring import ScoringEngine
from ..timezone_utils import timezone_utils

logger = get_logger(__name__)


class ResolutionService:
    """Resolves races and awards points to users."""

    def __init__(
        self,
        bet_service=None,
        user_service=None,
        race_manager=None,
        results_cache_file: str = None,
    ):
        if results_cache_file is None:
            results_cache_file = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "data", "race_results.json",
            )
        self._cache = JsonStore(results_cache_file, default={})
        self._bet_service = bet_service
        self._user_service = user_service
        self._race_manager = race_manager
        self._scoring: Optional[ScoringEngine] = None

    def set_dependencies(self, bet_service, user_service, race_manager) -> None:
        """Inject dependencies after construction to avoid circular imports."""
        self._bet_service = bet_service
        self._user_service = user_service
        self._race_manager = race_manager
        self._scoring = ScoringEngine(self._load_driver_teams())

    def _load_driver_teams(self) -> Dict[str, str]:
        """Build driver_id -> team_id mapping from drivers.json."""
        if not self._race_manager:
            return {}
        teams = {}
        for d in self._race_manager.load_drivers().get("drivers", []):
            did, tid = d.get("driverId"), d.get("teamId")
            if did and tid:
                teams[did] = tid
        return teams

    def refresh_driver_teams(self) -> None:
        """Rebuild the scoring engine's driver team mapping."""
        self._scoring = ScoringEngine(self._load_driver_teams())

    def set_driver_teams(self, teams: Dict[str, str]) -> None:
        """Override the driver team mapping (used by tests)."""
        self._scoring = ScoringEngine(teams)

    # -- Resolution ---------------------------------------------------------

    def resolve_with_results(
        self,
        race_id: str,
        top3_drivers: List[str],
        fastest_lap_driver: Optional[str] = None,
    ) -> Dict[str, dict]:
        """
        Resolve a race given the actual top-3 drivers and fastest lap.

        Returns:
            {username: {"total": int, "breakdown": {...}}}
        """
        if len(top3_drivers) != 3:
            logger.warning("Invalid results for %s: %d drivers", race_id, len(top3_drivers))
            return {}

        if not self._scoring:
            self.refresh_driver_teams()

        actual = ScoringEngine.build_actual_results(
            top3_drivers, self._scoring.driver_teams, fastest_lap_driver
        )

        data = self._bet_service.load_all()
        race_entry = data["race_bets"].get(race_id, {})
        user_bets = race_entry.get("user_bets", {})

        summary = {}
        for username, bet in user_bets.items():
            result = self._scoring.calculate(bet, actual)
            bet["points_awarded"] = result["total_points"]
            bet["points_breakdown"] = result["breakdown"]
            data["race_bets"][race_id]["user_bets"][username] = bet
            summary[username] = result

        # Mark race as resolved
        if race_id in data["race_bets"]:
            data["race_bets"][race_id]["status"] = "resolved"
            data["race_bets"][race_id]["resolved_at"] = timezone_utils.now_iso()

        self._bet_service.save_all(data)

        # Update user scores
        for username, result in summary.items():
            self._user_service.add_score(username, result["total_points"], race_id)

        return summary

    # -- F1 API integration -------------------------------------------------

    def fetch_from_api(self, race_id: str) -> Optional[Dict]:
        """Fetch race results from Jolpica (api.jolpi.ca) and cache them."""
        import requests

        if not self._race_manager:
            return None

        race = self._race_manager.get_race_by_id(race_id)
        if not race or not race.get("round"):
            logger.error("Cannot fetch results for %s: missing race/round", race_id)
            return None

        year = race_id.split("_")[-1]
        url = f"https://api.jolpi.ca/ergast/f1/{year}/{race['round']}/results.json"
        logger.info("Fetching race results from %s", url)

        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                logger.error("API returned %s for %s", resp.status_code, race_id)
                return None
            transformed = self._transform(resp.json(), race_id, url)
            cache = self._cache.load()
            cache[race_id] = transformed
            self._cache.save(cache)
            return transformed
        except Exception as e:
            logger.error("Error fetching results for %s: %s", race_id, e)
            return None

    def get_results(self, race_id: str) -> Optional[Dict]:
        """Get cached results, or fetch from API if not cached."""
        cached = self._cache.load().get(race_id)
        if cached:
            return cached
        return self.fetch_from_api(race_id)

    def resolve_from_api(self, race_id: str) -> bool:
        """Resolve a race using F1 API results."""
        results = self.get_results(race_id)
        if not results or len(results.get("results", [])) < 3:
            logger.error("Insufficient results for %s", race_id)
            return False

        top3 = [r["driverId"] for r in results["results"][:3] if r.get("driverId")]
        if len(top3) < 3:
            return False

        fl = None
        if results.get("overall_fastest_lap"):
            fl = results["overall_fastest_lap"].get("driverId")

        summary = self.resolve_with_results(race_id, top3, fl)
        return True  # resolved (even if no bets)

    def _transform(self, api_response: Dict, race_id: str, api_url: str) -> Dict:
        """Transform Ergast-format results response into our standard format."""
        try:
            raw = (
                api_response.get("MRData", {})
                .get("RaceTable", {})
                .get("Races", [{}])[0]
                .get("Results", [])
            )

            results = []
            for r in raw:
                driver = r.get("Driver", {})
                constructor = r.get("Constructor", {})
                fl = r.get("FastestLap", {})
                fl_time = fl.get("Time", {}).get("time") if fl else None
                entry = {
                    "position": r.get("position"),
                    "driverId": driver.get("driverId"),
                    "driverName": f"{driver.get('givenName', '')} {driver.get('familyName', '')}".strip(),
                    "driverNumber": r.get("number"),
                    "teamId": constructor.get("constructorId"),
                    "points": r.get("points", 0),
                    "fastLapTime": fl_time,
                    "fastLapRank": fl.get("rank") if fl else None,
                }
                results.append(entry)

            # Overall fastest lap = the rank-1 FastestLap entry
            fl_driver, fl_time = None, None
            for r in results:
                if r.get("fastLapRank") == "1":
                    fl_driver = r["driverId"]
                    fl_time = r.get("fastLapTime")
                    break
            if fl_driver is None:
                for r in results:
                    if r.get("fastLapTime") and (fl_time is None or r["fastLapTime"] < fl_time):
                        fl_time = r["fastLapTime"]
                        fl_driver = r["driverId"]

            out = {
                "fetched_at": timezone_utils.now_iso(),
                "api_url": api_url,
                "race_id": race_id,
                "results": results,
            }
            if fl_driver:
                out["overall_fastest_lap"] = {"driverId": fl_driver, "time": fl_time}
            return out

        except Exception as e:
            logger.error("Error transforming results for %s: %s", race_id, e)
            return {"race_id": race_id, "results": [], "error": str(e)}


# Singleton — dependencies injected after construction
resolution_service = ResolutionService()
