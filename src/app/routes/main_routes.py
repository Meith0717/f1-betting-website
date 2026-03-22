from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from ..utils import load_users, save_users, hash_password, verify_password
from ..decorators import login_required
from ..race_data import race_data_manager
from ..betting import betting_manager
from datetime import datetime
import pytz

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Handle the main index route - shows welcome page or user dashboard"""
    from flask import current_app
    
    current_app.logger.debug("Main index route accessed")
    
    # Get next race and session data with timezone info
    try:
        next_race = race_data_manager.get_next_race()
        current_app.logger.debug(f"Next race: {next_race['name'] if next_race else 'None'}")
        
        next_session = race_data_manager.get_next_session()
        current_app.logger.debug(f"Next session: {next_session['type'] if next_session else 'None'} for race {next_session.get('race_name', 'Unknown') if next_session else 'Unknown'}")
        
        upcoming_races = race_data_manager.get_upcoming_races(limit=3)
        current_app.logger.debug(f"Found {len(upcoming_races)} upcoming races")

        # Add timezone info to races
        if next_race:
            next_race = race_data_manager.add_timezone_info_to_race(next_race)
            current_app.logger.debug(f"Added timezone info to next race")

        # Add timezone info to next session if it exists
        if next_session:
            next_session = race_data_manager.add_timezone_info_to_session(next_session)
            current_app.logger.debug(f"Added timezone info to next session")

        upcoming_races = race_data_manager.add_timezone_info_to_races(upcoming_races)
        current_app.logger.debug(f"Added timezone info to {len(upcoming_races)} upcoming races")

    except Exception as e:
        current_app.logger.error(f"Error getting race data: {e}")
        next_race = None
        next_session = None
        upcoming_races = []

    if "username" in session:
        current_app.logger.debug(f"User session found: {session['username']}")
        # Show user dashboard with admin links if applicable
        try:
            users = load_users()
            current_app.logger.debug(f"Loaded {len(users)} users for dashboard")
            
            # Create sorted users list for leaderboard
            sorted_users = sorted(
                users.items(), key=lambda x: x[1].get("score", 0), reverse=True
            )

            # Find current user's rank
            current_username = session["username"]
            user_rank = next(
                (
                    i + 1
                    for i, (username, _) in enumerate(sorted_users)
                    if username == current_username
                ),
                None,
            )
            current_app.logger.debug(f"User {current_username} rank: {user_rank}")

            return render_template(
                "user/overview.html",
                username=session["username"],
                is_admin=session.get("is_admin", False),
                users=users,
                sorted_users=sorted_users,
                user_rank=user_rank,
                next_race=next_race,
                next_session=next_session,
                upcoming_races=upcoming_races,
                betting_manager=betting_manager,
                race_data_manager=race_data_manager,
            )
        except Exception as e:
            current_app.logger.error(f"Error rendering user dashboard: {e}")
            flash("Error loading dashboard data", "error")
            return redirect(url_for("main.index"))
    
    current_app.logger.debug("No user session, showing welcome page")
    return render_template("welcome.html")


@main_bp.route("/profile")
@login_required
def profile():
    """Show user profile page"""
    users = load_users()
    return render_template(
        "user/profile.html",
        username=session["username"],
        is_admin=session.get("is_admin", False),
        users=users,
        betting_manager=betting_manager,
    )


@main_bp.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    """Handle password change"""
    if request.method == "POST":
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        users = load_users()
        username = session["username"]

        # Validate current password
        if not verify_password(users[username]["password"], current_password):
            flash("Current password is incorrect", "error")
        elif new_password != confirm_password:
            flash("New passwords do not match", "error")
        elif len(new_password) < 6:
            flash("Password must be at least 6 characters", "error")
        else:
            # Update password
            users[username]["password"] = hash_password(new_password)
            save_users(users)
            flash("Password changed successfully!", "success")
            return redirect(url_for("main.profile"))

    return render_template("user/change_password.html", username=session["username"])


@main_bp.route("/change_email", methods=["GET", "POST"])
@login_required
def change_email():
    """Handle email change or setup"""
    if request.method == "POST":
        current_password = request.form.get("current_password")
        new_email = request.form.get("new_email")
        confirm_email = request.form.get("confirm_email")

        users = load_users()
        username = session["username"]

        # Validate current password
        if not verify_password(users[username]["password"], current_password):
            flash("Current password is incorrect", "error")
        elif not new_email or "@" not in new_email:
            flash("Please enter a valid email address", "error")
        elif new_email != confirm_email:
            flash("Email addresses do not match", "error")
        else:
            # Update or set email
            users[username]["email"] = new_email
            # If email was None before, this is first setup
            if users[username].get("email") is None:
                flash(
                    "Email set successfully! You can now receive notifications if enabled.",
                    "success",
                )
            else:
                flash("Email changed successfully!", "success")
            save_users(users)
            return redirect(url_for("main.profile"))

    users = load_users()
    return render_template(
        "user/change_email.html",
        username=session["username"],
        current_user=users[session["username"]],
    )


@main_bp.route("/races")
@login_required
def races():
    """Show all upcoming F1 races"""
    # Get all races and add timezone info
    all_races = race_data_manager.get_all_races()
    races_with_timezone = []
    upcoming_races = []
    past_races = []
    now = datetime.now(pytz.UTC)  # Make timezone-aware to match race datetimes

    for race in all_races:
        # Add timezone info to this race
        race_with_tz = race_data_manager.add_timezone_info_to_race(race)
        races_with_timezone.append(race_with_tz)

        # Classify as upcoming or past (include canceled races in upcoming if they're future-dated)
        race_datetime = race_data_manager._get_race_datetime(race)
        if race_datetime:
            # Ensure race_datetime is timezone-aware for comparison
            if not race_datetime.tzinfo:
                race_datetime = pytz.UTC.localize(race_datetime)
            if race_datetime > now:
                upcoming_races.append(race_with_tz)
            else:
                past_races.append(race_with_tz)

    return render_template(
        "races/list.html", upcoming_races=upcoming_races, past_races=past_races  #
    )


@main_bp.route("/update_notifications", methods=["POST"])
@login_required
def update_notifications():
    """Handle notification preference updates"""
    email_notifications = "email_notifications" in request.form
    users = load_users()
    username = session["username"]

    # Validate email exists if enabling notifications
    if email_notifications and not users[username].get("email"):
        flash(
            "Cannot enable email notifications: No email address set. Please set your email first.",
            "error",
        )
        return redirect(url_for("main.profile"))

    # Update and save
    users[username]["email_notifications"] = email_notifications
    save_users(users)
    flash("Notification preferences updated!", "success")

    return redirect(url_for("main.profile"))
