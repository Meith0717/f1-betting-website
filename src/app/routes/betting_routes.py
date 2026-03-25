from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from ..auth_decorators import login_required
from ..betting_manager import betting_manager
from ..race_data_manager import race_data_manager
from ..auth_utils import load_users
from datetime import datetime
import pytz

betting_bp = Blueprint("betting", __name__)


def _create_optimized_race_data(race):
    """Create optimized race data structure for templates."""
    return {
        "id": race.get("id"),
        "name": race.get("name"),
        "circuit": race.get("circuit"),
        "country": race.get("country"),
        "date": race.get("date"),
    }


@betting_bp.route("/betting")
@login_required
def betting_dashboard():
    """Show user's betting dashboard with closed and resolved bets"""
    try:
        from flask import current_app

        # Check and close any expired bets
        closed_count = betting_manager.check_and_close_expired_bets()
        if closed_count > 0:
            current_app.logger.info(
                f"Closed bets for {closed_count} races that have started"
            )

        # Get all betting data
        all_bets = betting_manager.get_all_bets()
        race_bets = all_bets.get("race_bets", {})

        # Get all races for context
        all_races = race_data_manager.get_all_races()
        race_dict = {race["id"]: race for race in all_races if race.get("id")}

        # Load drivers data for short names
        drivers_data = race_data_manager.load_drivers()
        driver_short_names = {}
        for driver in drivers_data.get("drivers", []):
            driver_id = driver.get("driverId")
            short_name = driver.get("shortName", "")
            if driver_id and short_name:
                driver_short_names[driver_id] = short_name

        # Prepare races with bets for template
        races_with_bets = {}
        races_without_bets = {}

        for race_id, race_bet_info in race_bets.items():
            # Only show closed or resolved races
            if race_bet_info.get("status") not in ["closed", "resolved"]:
                continue

            race_info = race_dict.get(
                race_id, {"name": f"Race {race_id}", "id": race_id}
            )
            user_bets = race_bet_info.get("user_bets", {})

            if user_bets:
                races_with_bets[race_id] = {
                    "race_info": race_info,
                    "race_bet_info": race_bet_info,
                    "bets": [],
                }

                # Add all user bets for this race
                for username, bet_data in user_bets.items():
                    # Convert driver IDs to short names
                    drivers_short = [
                        driver_short_names.get(d, d)
                        for d in bet_data.get("drivers", [])
                    ]
                    fastest_lap_short = driver_short_names.get(
                        bet_data.get("fastest_lap"), bet_data.get("fastest_lap", "-")
                    )

                    # Convert actual results if available
                    actual_results_short = []
                    if bet_data.get("actual_results"):
                        actual_results_short = [
                            driver_short_names.get(d, d)
                            for d in bet_data["actual_results"]
                        ]

                    races_with_bets[race_id]["bets"].append(
                        {
                            "username": username,
                            "drivers": bet_data.get("drivers", []),
                            "drivers_short": drivers_short,
                            "fastest_lap": bet_data.get("fastest_lap"),
                            "fastest_lap_short": fastest_lap_short,
                            "points_awarded": bet_data.get("points_awarded"),
                            "resolved_at": bet_data.get("resolved_at"),
                            "created_at": bet_data.get("created_at"),
                            "actual_results": bet_data.get("actual_results"),
                            "actual_results_short": actual_results_short,
                            "actual_fastest_lap": bet_data.get("actual_fastest_lap"),
                        }
                    )
            else:
                # Race has no bets
                races_without_bets[race_id] = {
                    "race_info": race_info,
                    "race_bet_info": race_bet_info,
                    "bets": [],
                }

        # Combine and sort all races by date (newest first)
        def get_race_date(race_data):
            race_info = race_data["race_info"]
            return race_info.get("date", "1970-01-01")

        # Sort both categories separately first
        races_with_bets = dict(
            sorted(
                races_with_bets.items(), key=lambda x: get_race_date(x[1]), reverse=True
            )
        )
        races_without_bets = dict(
            sorted(
                races_without_bets.items(),
                key=lambda x: get_race_date(x[1]),
                reverse=True,
            )
        )

        # Create combined list for display
        all_races_list = []

        # Merge races, interleaving by date
        races_with_bets_items = list(races_with_bets.items())
        races_without_bets_items = list(races_without_bets.items())

        i, j = 0, 0
        while i < len(races_with_bets_items) and j < len(races_without_bets_items):
            race_with_bets = races_with_bets_items[i]
            race_without_bets = races_without_bets_items[j]

            date_with = get_race_date(race_with_bets[1])
            date_without = get_race_date(race_without_bets[1])

            if date_with >= date_without:
                all_races_list.append(("with_bets", race_with_bets))
                i += 1
            else:
                all_races_list.append(("without_bets", race_without_bets))
                j += 1

        # Add remaining races
        while i < len(races_with_bets_items):
            all_races_list.append(("with_bets", races_with_bets_items[i]))
            i += 1

        while j < len(races_without_bets_items):
            all_races_list.append(("without_bets", races_without_bets_items[j]))
            j += 1

        # Convert back to separate dicts for template
        races_with_bets = {}
        races_without_bets = {}

        for race_type, (race_id, race_data) in all_races_list:
            if race_type == "with_bets":
                races_with_bets[race_id] = race_data
            else:
                races_without_bets[race_id] = race_data

        # Get current user info
        username = session["username"]
        users = load_users()
        is_admin = users.get(username, {}).get("is_admin", False)

        print(races_with_bets)

        return render_template(
            "betting/dashboard.html",
            username=username,
            races_with_bets=races_with_bets,
            races_without_bets=races_without_bets,
            betting_manager=betting_manager,
            is_admin=is_admin,
        )

    except Exception as e:
        from flask import current_app

        current_app.logger.error(f"Error in betting dashboard: {e}")
        import traceback

        current_app.logger.error(traceback.format_exc())
        flash("Error loading betting dashboard", "error")
        return redirect(url_for("main.index"))


@betting_bp.route("/betting/place/<race_id>", methods=["GET", "POST"])
@login_required
def place_bet(race_id):
    """Place a bet on a specific race"""
    try:
        username = session["username"]

        # Check if betting is allowed on this race
        if not betting_manager.can_bet_on_race(race_id, username):
            flash("Betting is not available for this race", "error")
            return redirect(url_for("betting.betting_dashboard"))

        # Get race and driver data
        race = race_data_manager.get_race_by_id(race_id)
        from flask import current_app

        current_app.logger.debug(f"Edit bet: Race found: {race is not None}")
        if not race:
            current_app.logger.error(f"Race not found for ID: {race_id}")
            flash("Race not found", "error")
            return redirect(url_for("betting.betting_dashboard"))

        current_app.logger.debug(
            f"Edit bet: Race ID from object: {race.get('id', 'NO ID FIELD')}"
        )
        drivers = betting_manager.get_available_drivers_for_race(race_id)
        current_app.logger.debug(f"Edit bet: Drivers found: {len(drivers)}")

        if request.method == "POST":
            # Get selected drivers from form
            position_1 = request.form.get("position_1")
            position_2 = request.form.get("position_2")
            position_3 = request.form.get("position_3")
            fastest_lap = request.form.get("fastest_lap")

            bets = [position_1, position_2, position_3]

            # Validate and place bet
            if betting_manager.place_bet(username, race_id, bets, fastest_lap):
                flash("Bet placed successfully!", "success")
                return redirect(url_for("main.index"))
            else:
                flash("Error placing bet. Please try again.", "error")

        return render_template(
            "betting/bet_form.html",
            mode="place",
            race=_create_optimized_race_data(race),
            drivers=drivers,
        )

    except Exception as e:
        from flask import current_app

        current_app.logger.error(f"Error processing bet in place_bet route: {e}")
        import traceback

        current_app.logger.error(traceback.format_exc())
        flash("Error processing bet", "error")
        return redirect(url_for("main.index"))


@betting_bp.route("/betting/edit/<race_id>", methods=["GET", "POST"])
@login_required
def edit_bet(race_id):
    """Edit an existing bet"""
    try:
        username = session["username"]

        if betting_manager.is_betting_closed(race_id):
            flash("You can no longer edit this bet.", "error")
            return redirect(url_for("main.index"))

        user_bets = betting_manager.get_user_bets(username)
        if race_id not in user_bets:
            flash("Bet not found", "error")
            return redirect(url_for("betting.betting_dashboard"))

        existing_bet = user_bets[race_id]
        # Check if bet has been resolved (has resolved_at timestamp)
        if existing_bet.get("resolved_at"):
            flash("Cannot edit a resolved bet", "error")
            return redirect(url_for("betting.betting_dashboard"))

        race = race_data_manager.get_race_by_id(race_id)
        if not race:
            flash("Race not found", "error")
            return redirect(url_for("betting.betting_dashboard"))

        drivers = betting_manager.get_available_drivers_for_race(race_id)

        if request.method == "POST":
            # Get selected drivers from form
            position_1 = request.form.get("position_1")
            position_2 = request.form.get("position_2")
            position_3 = request.form.get("position_3")
            fastest_lap = request.form.get("fastest_lap")

            bets = [position_1, position_2, position_3]

            # Remove old bet and place new one - new structure
            data = betting_manager.load_bets()
            if (
                race_id in data["race_bets"]
                and "user_bets" in data["race_bets"][race_id]
                and username in data["race_bets"][race_id]["user_bets"]
            ):
                del data["race_bets"][race_id]["user_bets"][username]

                # Remove race entry if no other users have bets
                if not data["race_bets"][race_id]["user_bets"]:
                    del data["race_bets"][race_id]

                betting_manager.save_bets(data)

            # Place new bet
            if betting_manager.place_bet(username, race_id, bets, fastest_lap):
                flash("Bet updated successfully!", "success")
                return redirect(url_for("main.index"))
            else:
                flash("Error updating bet. Please try again.", "error")

        return render_template(
            "betting/bet_form.html",
            mode="edit",
            race=_create_optimized_race_data(race),
            drivers=drivers,
            existing_bet=existing_bet,
        )

    except Exception as e:
        from flask import current_app

        current_app.logger.error(f"Error editing bet for race {race_id}: {e}")
        import traceback

        current_app.logger.error(traceback.format_exc())
        flash("Error editing bet", "error")
        return redirect(url_for("main.index"))


@betting_bp.route("/betting/cancel/<race_id>", methods=["POST"])
@login_required
def cancel_bet(race_id):
    """Cancel an existing bet"""
    try:
        username = session["username"]

        # Remove the bet - new structure
        data = betting_manager.load_bets()
        if betting_manager.is_betting_closed(race_id):
            flash("You can no longer delete this bet.", "error")
            return redirect(url_for("main.index"))

        if (
            race_id in data["race_bets"]
            and "user_bets" in data["race_bets"][race_id]
            and username in data["race_bets"][race_id]["user_bets"]
        ):
            # Check if race is closed (no individual bet status in new structure)
            race_status = data["race_bets"][race_id].get("status")
            if race_status == "closed" or race_status == "resolved":
                flash("Cannot cancel a closed or resolved bet", "error")
                return redirect(url_for("main.index"))

            del data["race_bets"][race_id]["user_bets"][username]

            # Remove race entry if no other users have bets
            if not data["race_bets"][race_id]["user_bets"]:
                del data["race_bets"][race_id]

            betting_manager.save_bets(data)
            flash("Bet canceled successfully!", "success")
        else:
            flash("Bet not found", "error")

        return redirect(url_for("main.index"))

    except Exception as e:
        flash("Error canceling bet", "error")
        return redirect(url_for("main.index"))


@betting_bp.route("/betting/history")
def betting_history():
    if "username" not in session:
        return redirect(url_for("auth.login"))

    username = session["username"]

    all_bets = betting_manager.get_all_bets()

    races_with_bets = {}

    # New structure: iterate through races and their bets
    for race_id, race_data in all_bets.get("races", {}).items():
        if "bets" not in race_data:
            continue

        for user, bet in race_data["bets"].items():
            # Check if bet is resolved or race is closed/resolved
            bet_is_resolved = bet.get("resolved_at") is not None
            race_status = race_data.get("status")

            if not (bet_is_resolved or race_status in ["closed", "resolved"]):
                continue

            race_info = race_data_manager.get_race_by_id(race_id)
            if not race_info:
                continue

            races_with_bets.setdefault(race_id, {"race_info": race_info, "bets": []})

            races_with_bets[race_id]["bets"].append({"username": user, "bet": bet})

    # Sort races by date (newest first)
    races_with_bets = dict(
        sorted(
            races_with_bets.items(),
            key=lambda x: x[1]["race_info"].get("date", ""),
            reverse=True,
        )
    )

    return render_template(
        "betting_history.html", races_with_bets=races_with_bets, username=username
    )


@betting_bp.route("/betting/resolve/<race_id>", methods=["POST"])
@login_required
def resolve_race_from_api(race_id):
    """Resolve a race by fetching results from F1 API"""
    try:
        # Check if user is admin
        users = load_users()
        username = session["username"]

        if not users.get(username, {}).get("is_admin", False):
            flash("Only admins can resolve races", "error")
            return redirect(url_for("betting.betting_dashboard"))

        # Resolve the race using API
        success = betting_manager.resolve_race_from_api(race_id)

        if success:
            flash(
                f"Race {race_id} resolved successfully using F1 API results!", "success"
            )
        else:
            flash(
                f"Failed to resolve race {race_id} from F1 API. The race may be too far in the future or the API may not have results yet. Try using manual resolution or check back later.",
                "error",
            )

        return redirect(url_for("betting.betting_dashboard"))

    except Exception as e:
        from flask import current_app

        current_app.logger.error(f"Error resolving race {race_id}: {e}")
        flash("Error resolving race", "error")
        return redirect(url_for("betting.betting_dashboard"))


@betting_bp.route("/betting/manual-resolve/<race_id>", methods=["GET", "POST"])
@login_required
def manual_resolve_race(race_id):
    """Manually resolve a race (for testing or when API unavailable)"""
    try:
        # Check if user is admin
        users = load_users()
        username = session["username"]

        if not users.get(username, {}).get("is_admin", False):
            flash("Only admins can manually resolve races", "error")
            return redirect(url_for("betting.betting_dashboard"))

        if request.method == "GET":
            # Show manual resolution form
            from .betting import betting_manager

            drivers = betting_manager.get_available_drivers_for_race(race_id)

            return render_template(
                "betting/manual_resolve.html", race_id=race_id, drivers=drivers
            )

        else:  # POST - process manual resolution
            # Get manual results from form
            driver_1 = request.form.get("position_1")
            driver_2 = request.form.get("position_2")
            driver_3 = request.form.get("position_3")
            fastest_lap = request.form.get("fastest_lap")

            if not all([driver_1, driver_2, driver_3, fastest_lap]):
                flash("Please select all positions and fastest lap", "error")
                return redirect(url_for("betting.manual_resolve_race", race_id=race_id))

            # Resolve the race with manual results
            actual_results = [driver_1, driver_2, driver_3]
            success = betting_manager.resolve_race_with_fastest_lap(
                race_id, actual_results, fastest_lap
            )

            if success:
                flash(
                    f"Race {race_id} resolved successfully with manual results!",
                    "success",
                )
            else:
                flash(f"Failed to resolve race {race_id} with manual results", "error")

            return redirect(url_for("betting.betting_dashboard"))

    except Exception as e:
        from flask import current_app

        current_app.logger.error(f"Error manually resolving race {race_id}: {e}")
        flash("Error manually resolving race", "error")
        return redirect(url_for("betting.betting_dashboard"))
