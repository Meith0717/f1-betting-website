"""
View-model builders — transform service data into template-ready structures.

Keeps data-shaping logic out of route handlers and templates.
"""

from typing import Dict, Tuple


def race_summary(race: Dict) -> Dict:
    """Minimal race dict for bet form templates."""
    return {
        "id": race.get("id"),
        "name": race.get("name"),
        "circuit": race.get("circuit"),
        "country": race.get("country"),
        "date": race.get("date"),
    }


def build_betting_dashboard(bet_service, race_manager, resolution_service=None, username: str = None) -> Dict:
    """
    Build {race_id: entry} for the betting dashboard — all past closed/resolved
    races (including those with no bets), sorted newest first by race date.

    If username is given, each race's "bets" list contains only that user's bet,
    and "bet_count" / "has_others" indicate whether a details page is useful.
    """
    all_bets = bet_service.load_all()
    race_bets = all_bets.get("race_bets", {})
    race_dict = {r["id"]: r for r in race_manager.get_all_races() if r.get("id")}
    short_names = race_manager.get_driver_short_names()

    combined: Dict = {}

    def _race_date(r: Dict) -> str:
        """Get the race date from the last session, falling back to top-level date."""
        sessions = r.get("sessions", [])
        if sessions and sessions[-1].get("date"):
            return sessions[-1]["date"]
        return r.get("date", "")

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
        # When filtering by user, only include their own bet
        display_bets = {username: user_bets[username]} if username and username in user_bets else user_bets
        entry = {
            "race_info": race_info,
            "race_bet_info": info,
            "race_results": race_results,
            "bet_count": len(user_bets),
            "has_others": len(user_bets) > (1 if username and username in user_bets else 0),
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
                for uname, bd in display_bets.items()
            ],
        }
        combined[race_id] = entry

    # Include past races with no bet entry at all
    from ..timezone_utils import timezone_utils
    now = timezone_utils.utc_now()
    for race_id, race_info in race_dict.items():
        if race_id in combined or race_info.get("canceled"):
            continue
        race_dt = race_manager.get_race_datetime(race_info)
        if race_dt and race_dt <= now:
            combined[race_id] = {
                "race_info": race_info,
                "race_bet_info": {"status": "closed", "user_bets": {}},
                "race_results": None,
                "bet_count": 0,
                "has_others": False,
                "bets": [],
            }

    # Sort all races newest first by actual race date
    return dict(sorted(
        combined.items(),
        key=lambda x: _race_date(x[1]["race_info"]),
        reverse=True,
    ))


def build_overview_context(bet_service, race_manager, username: str, next_race, next_session) -> Dict:
    """
    Pre-compute all data the overview template needs so it doesn't call
    service methods inline.
    """
    ctx = {
        "can_bet": False,
        "user_bets": {},
        "active_bets": [],
        "next_session_iso": "",
        "next_race_iso": "",
    }

    if next_race:
        ctx["can_bet"] = bet_service.can_bet_on_race(next_race.get("id"), username)
        ctx["next_race_iso"] = race_manager.get_race_datetime(next_race).isoformat()

    if next_session:
        ctx["next_session_iso"] = race_manager.get_session_datetime(next_session).isoformat()

    user_bets = bet_service.get_user_bets(username)
    ctx["user_bets"] = user_bets

    # Pre-compute race info and bet status for each active bet
    all_bets = bet_service.load_all()
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
