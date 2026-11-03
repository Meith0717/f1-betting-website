from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from ..auth_decorators import login_required
from ..betting_manager import betting_manager
from ..race_data_manager import race_data_manager
from ..auth_utils import load_users

betting_bp = Blueprint("betting", __name__)


def _race_summary(race):
    """Minimal race dict for templates."""
    return {
        "id": race.get("id"),
        "name": race.get("name"),
        "circuit": race.get("circuit"),
        "country": race.get("country"),
        "date": race.get("date"),
    }


def _build_dashboard_data():
    """
    Build the races_with_bets / races_without_bets dicts for the betting dashboard.
    All business logic extracted from the route handler.
    """
    all_bets = betting_manager.get_all_bets()
    race_bets = all_bets.get("race_bets", {})
    race_dict = {r["id"]: r for r in race_data_manager.get_all_races() if r.get("id")}
    short_names = race_data_manager.get_driver_short_names()

    with_bets, without_bets = {}, {}

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
                    "fastest_lap_short": short_names.get(bd.get("fastest_lap"), bd.get("fastest_lap", "-")),
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

    # Sort both by race date, newest first
    def by_date(d):
        return sorted(d.items(), key=lambda x: x[1]["race_info"].get("date", "1970-01-01"), reverse=True)

    return dict(by_date(with_bets)), dict(by_date(without_bets))


@betting_bp.route("/betting")
@login_required
def betting_dashboard():
    """Show closed/resolved bets grouped by race."""
    try:
        from flask import current_app

        closed = betting_manager.check_and_close_expired_bets()
        if closed:
            current_app.logger.info(f"Closed bets for {closed} races")

        races_with_bets, races_without_bets = _build_dashboard_data()
        username = session["username"]
        is_admin = load_users().get(username, {}).get("is_admin", False)

        return render_template(
            "betting/dashboard.html",
            username=username,
            races_with_bets=races_with_bets,
            races_without_bets=races_without_bets,
            betting_manager=betting_manager,
            is_admin=is_admin,
            driver_short_names=race_data_manager.get_driver_short_names(),
            driver_teams=race_data_manager.get_driver_teams(),
        )
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Error in betting dashboard: {e}")
        flash("Error loading betting dashboard", "error")
        return redirect(url_for("main.index"))


@betting_bp.route("/betting/place/<race_id>", methods=["GET", "POST"])
@login_required
def place_bet(race_id):
    """Place a bet on a specific race."""
    username = session["username"]

    if not betting_manager.can_bet_on_race(race_id, username):
        flash("Betting is not available for this race", "error")
        return redirect(url_for("betting.betting_dashboard"))

    race = race_data_manager.get_race_by_id(race_id)
    if not race:
        flash("Race not found", "error")
        return redirect(url_for("betting.betting_dashboard"))

    if request.method == "POST":
        bets = [
            request.form.get("position_1"),
            request.form.get("position_2"),
            request.form.get("position_3"),
        ]
        fastest_lap = request.form.get("fastest_lap")

        if betting_manager.place_bet(username, race_id, bets, fastest_lap):
            flash("Bet placed successfully!", "success")
            return redirect(url_for("main.index"))
        flash("Error placing bet. Please try again.", "error")

    return render_template(
        "betting/bet_form.html",
        mode="place",
        race=_race_summary(race),
        drivers=betting_manager.get_available_drivers_for_race(race_id),
    )


@betting_bp.route("/betting/edit/<race_id>", methods=["GET", "POST"])
@login_required
def edit_bet(race_id):
    """Edit an existing bet."""
    username = session["username"]

    if betting_manager.is_betting_closed(race_id):
        flash("You can no longer edit this bet.", "error")
        return redirect(url_for("main.index"))

    existing = betting_manager.get_user_bets(username).get(race_id)
    if not existing:
        flash("Bet not found", "error")
        return redirect(url_for("betting.betting_dashboard"))
    if existing.get("resolved_at"):
        flash("Cannot edit a resolved bet", "error")
        return redirect(url_for("betting.betting_dashboard"))

    race = race_data_manager.get_race_by_id(race_id)
    if not race:
        flash("Race not found", "error")
        return redirect(url_for("betting.betting_dashboard"))

    if request.method == "POST":
        bets = [
            request.form.get("position_1"),
            request.form.get("position_2"),
            request.form.get("position_3"),
        ]
        fastest_lap = request.form.get("fastest_lap")

        # Remove old bet, place new one
        from ..services import bet_service
        bet_service.remove_bet(username, race_id)

        if betting_manager.place_bet(username, race_id, bets, fastest_lap):
            flash("Bet updated successfully!", "success")
            return redirect(url_for("main.index"))
        flash("Error updating bet. Please try again.", "error")

    return render_template(
        "betting/bet_form.html",
        mode="edit",
        race=_race_summary(race),
        drivers=betting_manager.get_available_drivers_for_race(race_id),
        existing_bet=existing,
    )


@betting_bp.route("/betting/cancel/<race_id>", methods=["POST"])
@login_required
def cancel_bet(race_id):
    """Cancel an existing bet."""
    username = session["username"]

    if betting_manager.is_betting_closed(race_id):
        flash("You can no longer delete this bet.", "error")
        return redirect(url_for("main.index"))

    status = betting_manager.get_all_bets().get("race_bets", {}).get(race_id, {}).get("status")
    if status in ("closed", "resolved"):
        flash("Cannot cancel a closed or resolved bet", "error")
        return redirect(url_for("main.index"))

    from ..services import bet_service
    if bet_service.remove_bet(username, race_id):
        flash("Bet canceled successfully!", "success")
    else:
        flash("Bet not found", "error")

    return redirect(url_for("main.index"))


@betting_bp.route("/betting/history")
@login_required
def betting_history():
    """Show resolved/closed bet history for the current user."""
    username = session["username"]
    all_bets = betting_manager.get_all_bets()
    short_names = race_data_manager.get_driver_short_names()

    races_with_bets = {}
    for race_id, race_data in all_bets.get("race_bets", {}).items():
        user_bets = race_data.get("user_bets", {})
        if not user_bets:
            continue

        race_status = race_data.get("status")
        resolved_bets = {
            u: b for u, b in user_bets.items()
            if b.get("resolved_at") or race_status in ("closed", "resolved")
        }
        if not resolved_bets:
            continue

        race_info = race_data_manager.get_race_by_id(race_id)
        if not race_info:
            continue

        races_with_bets[race_id] = {
            "race_info": race_info,
            "bets": [
                {
                    "username": u,
                    "drivers_short": [short_names.get(d, d) for d in b.get("drivers", [])],
                    "fastest_lap_short": short_names.get(b.get("fastest_lap"), "-"),
                    "points_awarded": b.get("points_awarded"),
                    "bet": b,
                }
                for u, b in resolved_bets.items()
            ],
        }

    races_with_bets = dict(sorted(
        races_with_bets.items(),
        key=lambda x: x[1]["race_info"].get("date", ""),
        reverse=True,
    ))

    return render_template(
        "betting_history.html", races_with_bets=races_with_bets, username=username
    )


@betting_bp.route("/betting/resolve/<race_id>", methods=["POST"])
@login_required
def resolve_race_from_api(race_id):
    """Resolve a race via F1 API (admin only)."""
    username = session["username"]
    if not load_users().get(username, {}).get("is_admin", False):
        flash("Only admins can resolve races", "error")
        return redirect(url_for("betting.betting_dashboard"))

    if betting_manager.resolve_race_from_api(race_id):
        flash(f"Race {race_id} resolved successfully using F1 API results!", "success")
    else:
        flash(f"Failed to resolve race {race_id} from F1 API.", "error")

    return redirect(url_for("betting.betting_dashboard"))


@betting_bp.route("/betting/manual-resolve/<race_id>", methods=["GET", "POST"])
@login_required
def manual_resolve_race(race_id):
    """Manually resolve a race (admin only)."""
    username = session["username"]
    if not load_users().get(username, {}).get("is_admin", False):
        flash("Only admins can manually resolve races", "error")
        return redirect(url_for("betting.betting_dashboard"))

    if request.method == "GET":
        return render_template(
            "betting/manual_resolve.html",
            race_id=race_id,
            drivers=betting_manager.get_available_drivers_for_race(race_id),
        )

    # POST
    results = [
        request.form.get("position_1"),
        request.form.get("position_2"),
        request.form.get("position_3"),
    ]
    fastest_lap = request.form.get("fastest_lap")

    if not all(results + [fastest_lap]):
        flash("Please select all positions and fastest lap", "error")
        return redirect(url_for("betting.manual_resolve_race", race_id=race_id))

    if betting_manager.resolve_race_with_fastest_lap(race_id, results, fastest_lap):
        flash(f"Race {race_id} resolved successfully with manual results!", "success")
    else:
        flash(f"Failed to resolve race {race_id}", "error")

    return redirect(url_for("betting.betting_dashboard"))
