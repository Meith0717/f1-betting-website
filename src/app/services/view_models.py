"""
View-model builders — transform service data into template-ready structures.

Keeps data-shaping logic out of route handlers and templates.
"""

from typing import Dict, List, Tuple


def race_summary(race: Dict) -> Dict:
    """Minimal race dict for bet form templates."""
    return {
        "id": race.get("id"),
        "name": race.get("name"),
        "circuit": race.get("circuit"),
        "country": race.get("country"),
        "date": race.get("date"),
    }


def build_betting_dashboard(bet_service, race_manager, resolution_service=None) -> Tuple[Dict, Dict]:
    """
    Build (races_with_bets, races_without_bets) for the betting dashboard.

    Only includes closed/resolved, non-canceled races, sorted newest first.
    Pre-computes actual race results so the template doesn't call managers inline.
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

        # Pre-compute actual results for resolved races
        race_results = None
        if info.get("status") == "resolved" and resolution_service:
            raw = resolution_service.get_results(race_id)
            if raw and raw.get("results"):
                race_results = {
                    "top3": [
                        {
                            "driver_short": short_names.get(r.get("driverId"), r.get("driverId")),
                            "team": r.get("teamId"),
                        }
                        for r in raw["results"][:3]
                    ],
                    "fastest_lap_short": (
                        short_names.get(raw["overall_fastest_lap"]["driverId"])
                        if raw.get("overall_fastest_lap") else None
                    ),
                }

        user_bets = info.get("user_bets", {})
        target = with_bets if user_bets else without_bets
        entry = {
            "race_info": race_info,
            "race_bet_info": info,
            "race_results": race_results,
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
        target[race_id] = entry

    def _by_date(d: Dict) -> Dict:
        return dict(sorted(
            d.items(),
            key=lambda x: x[1]["race_info"].get("date", "1970-01-01"),
            reverse=True,
        ))

    return _by_date(with_bets), _by_date(without_bets)


def build_overview_context(betting_manager, race_manager, username: str, next_race, next_session) -> Dict:
    """
    Pre-compute all data the overview template needs so it doesn't call
    manager methods inline.
    """
    ctx = {
        "can_bet": False,
        "user_bets": {},
        "active_bets": [],
        "next_session_iso": "",
        "next_race_iso": "",
    }

    if next_race:
        ctx["can_bet"] = betting_manager.can_bet_on_race(next_race.get("id"), username)
        ctx["next_race_iso"] = race_manager.get_race_datetime(next_race).isoformat()

    if next_session:
        ctx["next_session_iso"] = race_manager.get_session_datetime(next_session).isoformat()

    user_bets = betting_manager.get_user_bets(username)
    ctx["user_bets"] = user_bets

    # Pre-compute race info and bet status for each active bet
    all_bets = betting_manager.get_all_bets()
    short_names = race_manager.get_driver_short_names()
    teams = race_manager.get_driver_teams()

    for race_id, bet_data in user_bets.items():
        race_info = race_manager.get_race_by_id(race_id)
        race_bet_info = all_bets.get("race_bets", {}).get(race_id, {})
        status = race_bet_info.get("status", "active")

        if status in ("closed", "resolved") or (race_info and race_info.get("canceled")):
            continue

        drivers = bet_data.get("drivers", [])
        ctx["active_bets"].append({
            "race_id": race_id,
            "race_name": race_info.get("name", "Unknown") if race_info else "Unknown",
            "drivers": drivers,
            "drivers_short": [short_names.get(d, d) for d in drivers],
            "driver_teams": [teams.get(d, "?") for d in drivers],
            "fastest_lap": bet_data.get("fastest_lap"),
            "fastest_lap_short": short_names.get(bet_data.get("fastest_lap"), "-"),
            "created_at": bet_data.get("created_at", ""),
        })

    return ctx
