from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from ..auth_decorators import login_required
from ..core.logger import get_logger
from ..race_data_manager import race_data_manager
from ..services import bet_service, user_service, resolution_service
from ..services.view_models import build_betting_dashboard, race_summary

logger = get_logger(__name__)

betting_bp = Blueprint("betting", __name__)


def _extract_bet_form() -> tuple:
    """Extract (drivers, fastest_lap) from the bet form POST data."""
    drivers = [
        request.form.get("position_1"),
        request.form.get("position_2"),
        request.form.get("position_3"),
    ]
    fastest_lap = request.form.get("fastest_lap")
    return drivers, fastest_lap


@betting_bp.route("/betting")
@login_required
def betting_dashboard():
    """Show closed/resolved bets grouped by race."""
    closed = bet_service.check_and_close_expired()
    if closed:
        logger.info("Closed bets for %d races", closed)

    races_with_bets, races_without_bets = build_betting_dashboard(
        bet_service, race_data_manager, resolution_service
    )
    username = session["username"]

    return render_template(
        "betting/dashboard.html",
        username=username,
        races_with_bets=races_with_bets,
        races_without_bets=races_without_bets,
        is_admin=user_service.is_admin(username),
        driver_short_names=race_data_manager.get_driver_short_names(),
        driver_teams=race_data_manager.get_driver_teams(),
    )


@betting_bp.route("/betting/place/<race_id>", methods=["GET", "POST"])
@login_required
def place_bet(race_id):
    """Place a bet on a specific race."""
    username = session["username"]

    if not bet_service.can_bet_on_race(race_id, username):
        flash("Betting is not available for this race", "error")
        return redirect(url_for("betting.betting_dashboard"))

    race = race_data_manager.get_race_by_id(race_id)
    if not race:
        flash("Race not found", "error")
        return redirect(url_for("betting.betting_dashboard"))

    if request.method == "POST":
        bets, fastest_lap = _extract_bet_form()

        if bet_service.place_bet(username, race_id, bets, fastest_lap):
            flash("Bet placed successfully!", "success")
            return redirect(url_for("main.index"))
        flash("Error placing bet. Please try again.", "error")

    return render_template(
        "betting/bet_form.html",
        mode="place",
        race=race_summary(race),
        drivers=bet_service.get_available_drivers(),
    )


@betting_bp.route("/betting/edit/<race_id>", methods=["GET", "POST"])
@login_required
def edit_bet(race_id):
    """Edit an existing bet."""
    username = session["username"]

    if bet_service.is_betting_closed(race_id):
        flash("You can no longer edit this bet.", "error")
        return redirect(url_for("main.index"))

    existing = bet_service.get_user_bets(username).get(race_id)
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
        bets, fastest_lap = _extract_bet_form()

        bet_service.remove_bet(username, race_id)

        if bet_service.place_bet(username, race_id, bets, fastest_lap):
            flash("Bet updated successfully!", "success")
            return redirect(url_for("main.index"))
        flash("Error updating bet. Please try again.", "error")

    return render_template(
        "betting/bet_form.html",
        mode="edit",
        race=race_summary(race),
        drivers=bet_service.get_available_drivers(),
        existing_bet=existing,
    )


@betting_bp.route("/betting/cancel/<race_id>", methods=["POST"])
@login_required
def cancel_bet(race_id):
    """Cancel an existing bet."""
    username = session["username"]

    if bet_service.is_betting_closed(race_id):
        flash("You can no longer delete this bet.", "error")
        return redirect(url_for("main.index"))

    status = bet_service.get_race_status(race_id)
    if status in ("closed", "resolved"):
        flash("Cannot cancel a closed or resolved bet", "error")
        return redirect(url_for("main.index"))

    if bet_service.remove_bet(username, race_id):
        flash("Bet canceled successfully!", "success")
    else:
        flash("Bet not found", "error")

    return redirect(url_for("main.index"))


@betting_bp.route("/betting/history")
@login_required
def betting_history():
    """Show resolved/closed bet history."""
    username = session["username"]
    all_bets = bet_service.load_all()
    short_names = race_data_manager.get_driver_short_names()

    races_with_bets = {}
    for race_id, race_data in all_bets.get("race_bets", {}).items():
        user_bets = race_data.get("user_bets", {})
        if not user_bets:
            continue

        race_status = race_data.get("status")
        resolved = {
            u: b for u, b in user_bets.items()
            if b.get("resolved_at") or race_status in ("closed", "resolved")
        }
        if not resolved:
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
                for u, b in resolved.items()
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
    if not user_service.is_admin(session["username"]):
        flash("Only admins can resolve races", "error")
        return redirect(url_for("betting.betting_dashboard"))

    if resolution_service.resolve_from_api(race_id):
        flash(f"Race {race_id} resolved successfully using F1 API results!", "success")
    else:
        flash(f"Failed to resolve race {race_id} from F1 API.", "error")

    return redirect(url_for("betting.betting_dashboard"))


@betting_bp.route("/betting/manual-resolve/<race_id>", methods=["GET", "POST"])
@login_required
def manual_resolve_race(race_id):
    """Manually resolve a race (admin only)."""
    if not user_service.is_admin(session["username"]):
        flash("Only admins can manually resolve races", "error")
        return redirect(url_for("betting.betting_dashboard"))

    if request.method == "GET":
        return render_template(
            "betting/manual_resolve.html",
            race_id=race_id,
            drivers=bet_service.get_available_drivers(),
        )

    results, fastest_lap = _extract_bet_form()

    if not all(results + [fastest_lap]):
        flash("Please select all positions and fastest lap", "error")
        return redirect(url_for("betting.manual_resolve_race", race_id=race_id))

    if resolution_service.resolve_with_results(race_id, results, fastest_lap):
        flash(f"Race {race_id} resolved successfully with manual results!", "success")
    else:
        flash(f"Failed to resolve race {race_id}", "error")

    return redirect(url_for("betting.betting_dashboard"))
