"""
View-model builders — transform service data into template-ready structures.

Keeps data-shaping logic out of route handlers.
"""

from typing import Dict, Tuple


def build_betting_dashboard(bet_service, race_manager) -> Tuple[Dict, Dict]:
    """
    Build (races_with_bets, races_without_bets) for the betting dashboard.

    Only includes closed/resolved, non-canceled races, sorted newest first.
    """
    all_bets = bet_service.load_all()
    race_bets = all_bets.get("race_bets", {})
    race_dict = {r["id"]: r for r in race_manager.get_all_races() if r.get("id")}
    short_names = race_manager.get_driver_short_names()

    with_bets: Dict = {}
    without_bets: Dict = {}

    for race_id, info in race_bets.items():
        if info.get("status") not in ("closed", "resolved"):
            continue
        race_info = race_dict.get(race_id, {"name": f"Race {race_id}", "id": race_id})
        if race_info.get("canceled"):
            continue

        user_bets = info.get("user_bets", {})
        target = with_bets if user_bets else without_bets
        target[race_id] = {
            "race_info": race_info,
            "race_bet_info": info,
            "bets": [
                {
                    "username": uname,
                    "drivers": bd.get("drivers", []),
                    "drivers_short": [short_names.get(d, d) for d in bd.get("drivers", [])],
                    "fastest_lap": bd.get("fastest_lap"),
                    "fastest_lap_short": short_names.get(
                        bd.get("fastest_lap"), bd.get("fastest_lap", "-")
                    ),
                    "points_awarded": bd.get("points_awarded"),
                    "points_breakdown": bd.get("points_breakdown", {}),
                    "resolved_at": bd.get("resolved_at"),
                    "created_at": bd.get("created_at"),
                    "actual_results": bd.get("actual_results"),
                    "actual_results_short": (
                        [short_names.get(d, d) for d in bd["actual_results"]]
                        if bd.get("actual_results") else []
                    ),
                }
                for uname, bd in user_bets.items()
            ],
        }

    def _by_date(d: Dict) -> Dict:
        return dict(sorted(
            d.items(),
            key=lambda x: x[1]["race_info"].get("date", "1970-01-01"),
            reverse=True,
        ))

    return _by_date(with_bets), _by_date(without_bets)


def race_summary(race: Dict) -> Dict:
    """Minimal race dict for bet form templates."""
    return {
        "id": race.get("id"),
        "name": race.get("name"),
        "circuit": race.get("circuit"),
        "country": race.get("country"),
        "date": race.get("date"),
    }
