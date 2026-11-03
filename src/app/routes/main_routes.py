from flask import Blueprint, render_template, session, redirect, url_for, request, flash, current_app
from ..auth_utils import load_users, save_users, hash_password, verify_password
from ..auth_decorators import login_required
from ..race_data_manager import race_data_manager
from ..betting_manager import betting_manager
from ..services.user_service import user_service
from ..services.view_models import build_overview_context
from datetime import datetime
import pytz

main_bp = Blueprint("main", __name__)


@main_bp.route("/legal-notice")
def legal_notice():
    """Legal notice and information page."""
    return render_template("legal_notice.html")


@main_bp.route("/help")
def help_page():
    """Help page explaining how to play the game."""
    return render_template("help.html")


@main_bp.route("/")
def index():
    """Main index — welcome page or user dashboard."""
    current_app.logger.info("Main index route accessed")

    # Race data with timezone info
    try:
        next_race = race_data_manager.get_next_race()
        next_session = race_data_manager.get_next_session()
        upcoming_races = race_data_manager.get_upcoming_races(limit=3)

        if next_race:
            next_race = race_data_manager.add_timezone_info_to_race(next_race)
        if next_session:
            next_session = race_data_manager.add_timezone_info_to_session(next_session)
        upcoming_races = race_data_manager.add_timezone_info_to_races(upcoming_races)
    except Exception as e:
        current_app.logger.error(f"Error getting race data: {e}")
        next_race, next_session, upcoming_races = None, None, []

    # Auto-close expired bets
    try:
        closed = betting_manager.check_and_close_expired_bets()
        if closed:
            current_app.logger.info(f"Closed bets for {closed} started races")
    except Exception as e:
        current_app.logger.error(f"Error checking expired bets: {e}")

    if "username" not in session:
        return render_template("welcome.html")

    # Logged-in user dashboard
    try:
        username = session["username"]
        users = load_users()
        leaderboard = user_service.get_leaderboard()
        rank = user_service.get_rank(username)
        overview = build_overview_context(
            betting_manager, race_data_manager, username, next_race, next_session
        )

        return render_template(
            "user/overview.html",
            username=username,
            is_admin=session.get("is_admin", False),
            users=users,
            sorted_users=leaderboard,
            user_rank=rank,
            next_race=next_race,
            next_session=next_session,
            upcoming_races=upcoming_races,
            driver_teams=race_data_manager.get_driver_teams(),
            driver_short_names=race_data_manager.get_driver_short_names(),
            **overview,
        )
    except Exception as e:
        current_app.logger.error(f"Error rendering dashboard: {e}")
        flash("Error loading dashboard data", "error")
        return redirect(url_for("main.index"))


@main_bp.route("/profile")
@login_required
def profile():
    """User profile page."""
    return render_template(
        "user/profile.html",
        username=session["username"],
        is_admin=session.get("is_admin", False),
        users=load_users(),
    )


@main_bp.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    """Handle password change."""
    if request.method == "POST":
        current = request.form.get("current_password")
        new = request.form.get("new_password")
        confirm = request.form.get("confirm_password")

        username = session["username"]
        users = load_users()

        if not verify_password(users[username]["password"], current):
            flash("Current password is incorrect", "error")
        elif new != confirm:
            flash("New passwords do not match", "error")
        elif len(new) < 6:
            flash("Password must be at least 6 characters", "error")
        else:
            users[username]["password"] = hash_password(new)
            save_users(users)
            flash("Password changed successfully!", "success")
            return redirect(url_for("main.profile"))

    return render_template("user/change_password.html", username=session["username"])


@main_bp.route("/races")
@login_required
def races():
    """Show all F1 races, split into upcoming and past."""
    now = datetime.now(pytz.UTC)
    upcoming, past = [], []

    for race in race_data_manager.get_all_races():
        race_tz = race_data_manager.add_timezone_info_to_race(race)
        race_dt = race_data_manager._get_race_datetime(race)
        if race_dt:
            if not race_dt.tzinfo:
                race_dt = pytz.UTC.localize(race_dt)
            if race_dt > now:
                upcoming.append(race_tz)
            elif not race.get("canceled"):
                past.append(race_tz)

    return render_template(
        "races/list.html", upcoming_races=upcoming, past_races=past
    )
