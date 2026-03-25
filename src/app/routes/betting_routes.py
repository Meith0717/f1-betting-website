from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from ..decorators import login_required
from ..betting import betting_manager
from ..race_data import race_data_manager
from ..utils import load_users
from datetime import datetime
import pytz

betting_bp = Blueprint("betting", __name__)


@betting_bp.route("/betting")
@login_required
def betting_dashboard():
    """Show user's betting dashboard with resolved bets only"""
    try:
        from flask import current_app
        # Check and close any expired bets
        closed_count = betting_manager.check_and_close_expired_bets()
        if closed_count > 0:
            current_app.logger.info(f"Closed bets for {closed_count} races that have started")
        
        # Get user's bets
        username = session["username"]
        users = load_users()  # Load all users to check admin status
        user_bets = betting_manager.get_user_bets(username)
        
        # Get all races for context
        all_races = race_data_manager.get_all_races()
        # Add timezone info to races
        all_races = race_data_manager.add_timezone_info_to_races(all_races)
        race_dict = {}
        for race in all_races:
            try:
                race_dict[race["id"]] = race
            except (KeyError, TypeError):
                # Skip races without proper ID
                continue
        
        # Collect closed and resolved bets
        closed_resolved_bets = []
        
        for race_id, bet_data in user_bets.items():
            # Skip if bet_data is not a proper dictionary
            if not isinstance(bet_data, dict):
                continue
                
            # Check if bet is resolved (has resolved_at) or race is closed/resolved
            bet_is_resolved = bet_data.get("resolved_at") is not None
            race_status = race_dict.get(race_id, {}).get("status")
            
            # Get race info for all bets
            race_info = race_dict.get(race_id, {"name": "Unknown Race", "id": race_id})
            bet_data["race_info"] = race_info
            
            # Get bet status
            bet_status = bet_data.get("status", "")
            
            # Include if bet is resolved or race is closed/resolved
            if bet_is_resolved or race_status in ["closed", "resolved"]:
                # Use session times for proper race datetime
                if race_info and race_info.get("sessions"):
                    try:
                        # Find the first future session to determine when betting closes
                        now = datetime.now()
                        first_future_session = None
                        
                        for race_session in race_info["sessions"]:
                            if race_session.get("time"):
                                # Use timezone-converted time if available
                                if race_session.get("time_info"):
                                    # Use the already converted local time
                                    session_time = race_session["time_info"].get("datetime_obj")
                                    if session_time:
                                        # Ensure we're comparing compatible datetimes
                                        if hasattr(session_time, 'tzinfo') and session_time.tzinfo is not None:
                                            # Timezone-aware datetime, make now timezone-aware for comparison
                                            if not hasattr(now, 'tzinfo') or now.tzinfo is None:
                                                now = datetime.now(pytz.UTC)
                                            if session_time > now:
                                                first_future_session = race_session
                                                break
                                        else:
                                            # Naive datetime, ensure now is also naive
                                            if hasattr(now, 'tzinfo') and now.tzinfo is not None:
                                                now = datetime.now()  # Make naive
                                            if session_time > now:
                                                first_future_session = race_session
                                                break
                                else:
                                    # Fallback to parsing raw time string
                                    session_time_str = race_session["time"]
                                    # Handle different time formats
                                    if "T" in session_time_str:
                                        session_time = datetime.fromisoformat(session_time_str.replace("Z", "+00:00"))
                                    else:
                                        # Fallback for other formats
                                        session_time = datetime.strptime(session_time_str, "%Y-%m-%d %H:%M:%S")
                                    
                                    if session_time > now:
                                        first_future_session = race_session
                                        break
                    
                        if first_future_session:
                            bet_data["race_datetime"] = first_future_session.get("time", "")
                            bet_data["betting_closes_at"] = first_future_session.get("time", "")
                        else:
                            # If no future sessions, use the last session time
                            bet_data["race_datetime"] = race_info["sessions"][-1].get("time", "") if race_info["sessions"] else ""
                    except Exception as e:
                        current_app.logger.error(f"Error getting race session time: {e}")
                        bet_data["race_datetime"] = ""
                        bet_data["betting_closes_at"] = ""
                
                if bet_status == "resolved" or bet_status == "closed":
                    closed_resolved_bets.append(bet_data)
        
        # Sort by race date (newest first)
        closed_resolved_bets.sort(key=lambda x: x["race_info"].get("date", ""), reverse=True)
        
        # Group all bets by race for the new template structure
        races_with_bets = {}
        
        # Load drivers data for short names
        drivers_data = race_data_manager.load_drivers()
        driver_short_names = {}
        for driver in drivers_data.get("drivers", []):
            driver_id = driver.get("driverId")
            short_name = driver.get("shortName", "")
            if driver_id and short_name:
                driver_short_names[driver_id] = short_name
        
        # Add current user's bets
        for bet_data in closed_resolved_bets:
            race_id = bet_data["race_info"]["id"]
            if race_id not in races_with_bets:
                races_with_bets[race_id] = {
                    "race_info": bet_data["race_info"],
                    "bets": []
                }
            
            # Convert driver IDs to short names for predictions
            drivers_with_short_names = []
            for driver_id in bet_data["drivers"]:
                drivers_with_short_names.append(driver_short_names.get(driver_id, driver_id))
            bet_data["drivers_short"] = drivers_with_short_names
            
            # Add fastest lap support (placeholder for future implementation)
            fastest_lap = bet_data.get("fastest_lap")
            if fastest_lap:
                bet_data["fastest_lap_short"] = driver_short_names.get(fastest_lap, fastest_lap)
            else:
                bet_data["fastest_lap_short"] = None
            
            # Convert driver IDs to short names for actual results if available
            if bet_data.get("actual_results"):
                actual_results_short = []
                for driver_id in bet_data["actual_results"]:
                    actual_results_short.append(driver_short_names.get(driver_id, driver_id))
                bet_data["actual_results_short"] = actual_results_short
            
            races_with_bets[race_id]["bets"].append({
                "username": username,
                "bet": bet_data
            })
        
        # Get other users' betting history and add to race grouping
        try:
            all_users = load_users()
        except Exception as e:
            current_app.logger.error(f"Error loading users for betting history: {e}")
            all_users = {}
        
        for other_username, user_data in all_users.items():
            if other_username != username:  # Skip current user
                other_user_bets = betting_manager.get_user_bets(other_username)
                if other_user_bets:
                    for race_id, bet_data in other_user_bets.items():
                        # Skip if bet_data is not a proper dictionary
                        if not isinstance(bet_data, dict):
                            continue
                            
                        bet_status = bet_data.get("status")
                        if bet_status in ["resolved", "closed"]:
                            race_info = race_dict.get(race_id, {"name": "Unknown Race", "id": race_id})
                            bet_data["race_info"] = race_info
                            bet_data["bet_status"] = bet_status
                            
                            # Convert driver IDs to short names for predictions
                            drivers_with_short_names = []
                            for driver_id in bet_data["drivers"]:
                                drivers_with_short_names.append(driver_short_names.get(driver_id, driver_id))
                            bet_data["drivers_short"] = drivers_with_short_names
                            
                            # Add fastest lap support (placeholder for future implementation)
                            fastest_lap = bet_data.get("fastest_lap")
                            if fastest_lap:
                                bet_data["fastest_lap_short"] = driver_short_names.get(fastest_lap, fastest_lap)
                            else:
                                bet_data["fastest_lap_short"] = None
                            
                            # Convert driver IDs to short names for actual results if available
                            if bet_data.get("actual_results"):
                                actual_results_short = []
                                for driver_id in bet_data["actual_results"]:
                                    actual_results_short.append(driver_short_names.get(driver_id, driver_id))
                                bet_data["actual_results_short"] = actual_results_short
                            
                            # Add to race grouping
                            if race_id not in races_with_bets:
                                races_with_bets[race_id] = {
                                    "race_info": race_info,
                                    "bets": []
                                }
                            races_with_bets[race_id]["bets"].append({
                                "username": other_username,
                                "bet": bet_data
                            })
        
        # Sort races by date (newest first)
        races_with_bets = dict(sorted(
            races_with_bets.items(),
            key=lambda x: x[1]["race_info"].get("date", ""),
            reverse=True
        ))
        
        print("betting_dashboard")
        print(all_races)

        return render_template(
            "betting/dashboard.html",
            username=username,
            races_with_bets=races_with_bets,
            betting_manager=betting_manager,
            is_admin=users.get(username, {}).get("is_admin", False)
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
        
        current_app.logger.debug(f"Edit bet: Race ID from object: {race.get('id', 'NO ID FIELD')}")
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
            race=race,
            drivers=drivers,
            username=username
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
        if existing_bet["status"] != "active":
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
            if race_id in data["races"] and "bets" in data["races"][race_id] and username in data["races"][race_id]["bets"]:
                del data["races"][race_id]["bets"][username]
                
                # Remove race entry if no other users have bets
                if not data["races"][race_id]["bets"]:
                    del data["races"][race_id]
                
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
            race=race,
            drivers=drivers,
            username=username,
            existing_bet=existing_bet
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

        if race_id in data["races"] and "bets" in data["races"][race_id] and username in data["races"][race_id]["bets"]:
            bet_status = data["races"][race_id]["bets"][username]["status"]
            if bet_status != "active":
                flash("Cannot cancel a resolved bet", "error")
                return redirect(url_for("main.index"))
            
            del data["races"][race_id]["bets"][username]
            
            # Remove race entry if no other users have bets
            if not data["races"][race_id]["bets"]:
                del data["races"][race_id]
            
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

            races_with_bets.setdefault(
                race_id,
                {
                    "race_info": race_info,
                    "bets": []
                }
            )

            races_with_bets[race_id]["bets"].append({
                "username": user,
                "bet": bet
            })

    # Sort races by date (newest first)
    races_with_bets = dict(
        sorted(
            races_with_bets.items(),
            key=lambda x: x[1]["race_info"].get("date", ""),
            reverse=True
        )
    )

    return render_template(
        "betting_history.html",
        races_with_bets=races_with_bets,
        username=username
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
            flash(f"Race {race_id} resolved successfully using F1 API results!", "success")
        else:
            flash(f"Failed to resolve race {race_id} from F1 API. The race may be too far in the future or the API may not have results yet. Try using manual resolution or check back later.", "error")
            
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
                "betting/manual_resolve.html",
                race_id=race_id,
                drivers=drivers
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
                flash(f"Race {race_id} resolved successfully with manual results!", "success")
            else:
                flash(f"Failed to resolve race {race_id} with manual results", "error")
            
            return redirect(url_for("betting.betting_dashboard"))
            
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Error manually resolving race {race_id}: {e}")
        flash("Error manually resolving race", "error")
        return redirect(url_for("betting.betting_dashboard"))