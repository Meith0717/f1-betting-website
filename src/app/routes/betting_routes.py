from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from ..decorators import login_required
from ..betting import betting_manager
from ..race_data import race_data_manager
from datetime import datetime

betting_bp = Blueprint("betting", __name__)


@betting_bp.route("/betting")
@login_required
def betting_dashboard():
    """Show user's betting dashboard with resolved bets only"""
    try:
        # Get user's bets
        username = session["username"]
        user_bets = betting_manager.get_user_bets(username)
        
        # Get all races for context
        all_races = race_data_manager.get_all_races()
        race_dict = {race["id"]: race for race in all_races}
        
        # Only collect resolved bets (closed/past bets)
        resolved_bets = []
        
        for race_id, bet_data in user_bets.items():
            race_info = race_dict.get(race_id, {"name": "Unknown Race", "id": race_id})
            bet_data["race_info"] = race_info
            
            if bet_data["status"] == "resolved":
                resolved_bets.append(bet_data)
        
        # Sort by race date (newest first)
        resolved_bets.sort(key=lambda x: x["race_info"].get("date", ""), reverse=True)
        
        return render_template(
            "betting/dashboard.html",
            username=username,
            resolved_bets=resolved_bets,
            all_races=all_races,
            betting_manager=betting_manager
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
            
            bets = [position_1, position_2, position_3]
            
            # Validate and place bet
            if betting_manager.place_bet(username, race_id, bets):
                flash("Bet placed successfully!", "success")
                return redirect(url_for("betting.betting_dashboard"))
            else:
                flash("Error placing bet. Please try again.", "error")
        
        return render_template(
            "betting/place_bet.html",
            race=race,
            drivers=drivers,
            username=username
        )
        
    except Exception as e:
        flash("Error processing bet", "error")
        return redirect(url_for("betting.betting_dashboard"))


@betting_bp.route("/betting/edit/<race_id>", methods=["GET", "POST"])
@login_required
def edit_bet(race_id):
    """Edit an existing bet"""
    try:
        username = session["username"]
        
        # Get existing bet
        user_bets = betting_manager.get_user_bets(username)
        if race_id not in user_bets:
            flash("Bet not found", "error")
            return redirect(url_for("betting.betting_dashboard"))
        
        existing_bet = user_bets[race_id]
        if existing_bet["status"] != "active":
            flash("Cannot edit a resolved bet", "error")
            return redirect(url_for("betting.betting_dashboard"))
        
        # Get race and driver data
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
            
            bets = [position_1, position_2, position_3]
            
            # Remove old bet and place new one
            data = betting_manager.load_bets()
            if username in data["bets"] and race_id in data["bets"][username]:
                del data["bets"][username][race_id]
                
                # Remove from race tracking if no other users have bets
                if race_id in data["races"] and username in data["races"][race_id]["users"]:
                    data["races"][race_id]["users"].remove(username)
                    if not data["races"][race_id]["users"]:
                        del data["races"][race_id]
                
                betting_manager.save_bets(data)
            
            # Place new bet
            if betting_manager.place_bet(username, race_id, bets):
                flash("Bet updated successfully!", "success")
                return redirect(url_for("betting.betting_dashboard"))
            else:
                flash("Error updating bet. Please try again.", "error")
        
        return render_template(
            "betting/edit_bet.html",
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
        return redirect(url_for("betting.betting_dashboard"))


@betting_bp.route("/betting/cancel/<race_id>", methods=["POST"])
@login_required
def cancel_bet(race_id):
    """Cancel an existing bet"""
    try:
        username = session["username"]
        
        # Remove the bet
        data = betting_manager.load_bets()
        if username in data["bets"] and race_id in data["bets"][username]:
            bet_status = data["bets"][username][race_id]["status"]
            if bet_status != "active":
                flash("Cannot cancel a resolved bet", "error")
                return redirect(url_for("betting.betting_dashboard"))
            
            del data["bets"][username][race_id]
            
            # Remove from race tracking if no other users have bets
            if race_id in data["races"] and username in data["races"][race_id]["users"]:
                data["races"][race_id]["users"].remove(username)
                if not data["races"][race_id]["users"]:
                    del data["races"][race_id]
            
            betting_manager.save_bets(data)
            flash("Bet canceled successfully!", "success")
        else:
            flash("Bet not found", "error")
            
        return redirect(url_for("betting.betting_dashboard"))
        
    except Exception as e:
        flash("Error canceling bet", "error")
        return redirect(url_for("betting.betting_dashboard"))