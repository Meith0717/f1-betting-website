from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from ..utils import load_users, save_users, hash_password, verify_password
from ..decorators import login_required
from ..race_data import race_data_manager
from datetime import datetime

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Handle the main index route - shows welcome page or user dashboard"""
    # Get next race and session data with timezone info
    next_race = race_data_manager.get_next_race()
    next_session = race_data_manager.get_next_session()
    upcoming_races = race_data_manager.get_upcoming_races(limit=3)
    
    # Add timezone info to races
    if next_race:
        next_race = race_data_manager.add_timezone_info_to_race(next_race)
    if next_session:
        # Next session already has race info, but add timezone to session itself
        session_with_info = next_session.copy()
        if 'date' in next_session and ('time' in next_session or 'time' in next_session):
            session_time = next_session.get('time', next_session.get('time', '00:00:00'))
            session_with_info['time_info'] = race_data_manager.convert_utc_to_local(next_session['date'], session_time)
        next_session = session_with_info
    
    upcoming_races = race_data_manager.add_timezone_info_to_races(upcoming_races)
    
    if "username" in session:
        # Show user dashboard with admin links if applicable
        users = load_users()
        return render_template(
            "dashboard.html",
            username=session["username"],
            is_admin=session.get("is_admin", False),
            users=users,
            next_race=next_race,
            next_session=next_session,
            upcoming_races=upcoming_races
        )
    return render_template("index.html", next_race=next_race, next_session=next_session)


@main_bp.route("/profile")
@login_required
def profile():
    """Show user profile page"""
    users = load_users()
    return render_template(
        "profile.html",
        username=session["username"],
        is_admin=session.get("is_admin", False),
        users=users,
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

    return render_template("change_password.html", username=session["username"])


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
        "change_email.html",
        username=session["username"],
        current_user=users[session["username"]],
    )


@main_bp.route("/races")
def races():
    """Show all upcoming F1 races"""
    # Get all races and add timezone info
    all_races = race_data_manager.get_all_races()
    races_with_timezone = []
    upcoming_races = []
    past_races = []
    now = datetime.now()
    
    for race in all_races:
        # Add timezone info to this race
        race_with_tz = race_data_manager.add_timezone_info_to_race(race)
        races_with_timezone.append(race_with_tz)
        
        # Classify as upcoming or past
        try:
            if 'time' in race:
                race_datetime = datetime.strptime(f"{race['date']} {race['time']}", "%Y-%m-%d %H:%M:%S")
            elif race.get('sessions'):
                first_session = race['sessions'][0]
                session_time = first_session.get('time', first_session.get('time_utc', '00:00:00'))
                race_datetime = datetime.strptime(f"{first_session['date']} {session_time}", "%Y-%m-%d %H:%M:%S")
            else:
                continue
            
            if race_datetime > now:
                upcoming_races.append(race_with_tz)
            else:
                past_races.append(race_with_tz)
        except (ValueError, KeyError):
            continue
    
    return render_template(
        "races.html",
        upcoming_races=upcoming_races,
        past_races=past_races,
        next_race=race_data_manager.add_timezone_info_to_race(race_data_manager.get_next_race()),
        next_session=_add_timezone_to_session(race_data_manager.get_next_session())
    )


def _add_timezone_to_session(session):
    """Helper to add timezone info to a session"""
    if not session:
        return None
    session = session.copy()
    if 'date' in session and ('time' in session or 'time' in session):
        session_time = session.get('time', session.get('time', '00:00:00'))
        session['time_info'] = race_data_manager.convert_utc_to_local(session['date'], session_time)
    return session

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
