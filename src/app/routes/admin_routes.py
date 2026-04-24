from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    current_app,
)
from ..auth_utils import load_users, save_users
from ..auth_decorators import admin_required
from ..race_data_manager import race_data_manager
from ..push_manager import push_manager
import os
import secrets


def get_registration_password():
    """Get the current registration password from environment variable"""
    return os.environ.get("REGISTRATION_PASSWORD", "f1betting2024")


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@admin_required
def admin_dashboard():
    """Admin dashboard with system statistics"""
    from flask import current_app

    current_app.logger.info("Admin dashboard route accessed")

    try:
        users = load_users()

        # Get registration password from environment or default
        registration_password = get_registration_password()

        # Calculate total points
        total_points = sum(user.get("score", 0) for user in users.values())

        # Create sorted users list for leaderboard
        sorted_users = sorted(
            users.items(), key=lambda x: x[1].get("score", 0), reverse=True
        )

        # Get all races for canceled race management
        races = race_data_manager.get_all_races()
        canceled_race_ids = race_data_manager.get_canceled_race_ids()

        # Get recent log entries
        log_file = (
            os.path.join(current_app.instance_path, "logs", "app.log")
            if current_app.instance_path
            else "logs/app.log"
        )
        log_entries = []

        try:
            if os.path.exists(log_file):
                with open(log_file, "r") as f:
                    # Read last 50 lines
                    lines = f.readlines()
                    log_entries = lines[-50:] if len(lines) > 50 else lines
                    # Reverse to show newest first
                    log_entries = log_entries[::-1]
            else:
                current_app.logger.debug(f"Log file not found: {log_file}")
        except Exception as log_error:
            current_app.logger.error(f"Error reading log file: {log_error}")
            log_entries = [f"Error reading log file: {log_error}"]

        return render_template(
            "admin/dashboard.html",
            users=users,
            registration_password=registration_password,
            total_points=total_points,
            sorted_users=sorted_users,
            races=races,
            canceled_race_ids=canceled_race_ids,
            log_entries=log_entries,
            log_file_exists=os.path.exists(log_file),
        )
    except Exception as e:
        current_app.logger.error(f"Error loading admin dashboard: {e}")
        flash("Error loading admin dashboard data", "error")
        return redirect(url_for("main.index"))


@admin_bp.route("/users/<username>/promote", methods=["POST"])
@admin_required
def promote_user(username):
    """Promote user to admin"""
    users = load_users()

    if username in users:
        users[username]["is_admin"] = True
        save_users(users)
        flash(f"User {username} promoted to admin", "success")
    else:
        flash(f"User {username} not found", "error")

    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/users/<username>/demote", methods=["POST"])
@admin_required
def demote_user(username):
    """Demote admin user to regular user"""
    users = load_users()

    if username not in users:
        flash(f"User {username} not found", "error")
        return redirect(url_for("admin.admin_dashboard"))

    # Only count admins once and reuse the result
    admin_count = _count_admins(users)
    is_admin_user = users[username].get("is_admin", False)

    if admin_count <= 1:
        flash(
            "Cannot demote the last admin user. At least one admin must remain.",
            "error",
        )
    elif is_admin_user:
        users[username]["is_admin"] = False
        save_users(users)
        flash(f"User {username} demoted from admin", "success")

    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/users/<username>/delete", methods=["POST"])
@admin_required
def delete_user(username):
    """Delete a user"""
    users = load_users()
    current_username = session.get("username")

    # Prevent self-deletion
    if username == current_username:
        flash("Cannot delete your own account", "error")
        return redirect(url_for("admin.admin_dashboard"))

    if username not in users:
        flash(f"User {username} not found", "error")
        return redirect(url_for("admin.admin_dashboard"))

    # Count admins once and reuse
    admin_count = _count_admins(users)
    is_admin_user = users[username].get("is_admin", False)

    if is_admin_user and admin_count <= 1:
        flash(
            "Cannot delete the last admin user. At least one admin must remain.",
            "error",
        )
    else:
        del users[username]
        save_users(users)
        flash(f"User {username} deleted successfully", "success")

    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/users/<username>/send-test-notification", methods=["POST"])
@admin_required
def send_test_notification(username):
    """Send a test push notification to a specific user"""
    import pywebpush
    import json as json_module
    
    users = load_users()
    
    if username not in users:
        flash(f"User {username} not found", "error")
        return redirect(url_for("admin.admin_dashboard"))
    
    # Get VAPID keys
    public_key = os.environ.get('VAPID_PUBLIC_KEY')
    private_key = os.environ.get('VAPID_PRIVATE_KEY')
    claim_email = os.environ.get('VAPID_CLAIM_EMAIL', 'mailto:f1betting@icloud.com')
    
    if not public_key or not private_key:
        current_app.logger.error("VAPID keys not configured for admin test notification")
        flash("Push notifications not configured (missing VAPID keys)", "error")
        return redirect(url_for("admin.admin_dashboard"))
    
    # Get user's subscriptions
    subscriptions = push_manager.get_user_subscriptions(username)
    
    if not subscriptions:
        flash(f"{username} has no active push subscriptions", "info")
        return redirect(url_for("admin.admin_dashboard"))
    
    sent = 0
    failed = 0
    errors = []
    
    # Prepare notification payload
    payload = {
        'title': 'Test Notification',
        'body': f'Hello {username}! This is a test notification from the admin.',
        'data': {"test": True, "from_admin": True},
        'url': '/'
    }
    
    # Send to each subscription
    for subscription in subscriptions:
        try:
            subscription_info = {
                'endpoint': subscription['endpoint'],
                'keys': {
                    'p256dh': subscription['p256dh'],
                    'auth': subscription['auth']
                }
            }
            
            pywebpush.webpush(
                subscription_info=subscription_info,
                data=json_module.dumps(payload),
                vapid_private_key=private_key,
                vapid_claims={'sub': claim_email}
            )
            sent += 1
        except Exception as e:
            failed += 1
            errors.append(str(e))
            current_app.logger.error(f"Error sending push to {username}: {e}")
    
    if sent > 0:
        flash(f"Test notification sent to {username} ({sent} device(s))", "success")
    else:
        flash(f"Failed to send notification to {username}: {errors[0] if errors else 'Unknown error'}", "error")
    
    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/change-registration-password", methods=["POST"])
@admin_required
def change_registration_password():
    """Generate a new random registration password"""
    # Generate new random registration password
    new_password = secrets.token_urlsafe(16)
    # Set environment variable (this will only affect current process)
    os.environ["REGISTRATION_PASSWORD"] = new_password

    flash(f"Registration password has been changed to: {new_password}", "success")
    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/reset-all-points", methods=["POST"])
@admin_required
def reset_all_points():
    """Reset all user points to 0"""
    users = load_users()

    # Reset all user scores to 0
    for username, user_data in users.items():
        users[username]["score"] = 0

    save_users(users)
    flash("All user points have been reset to 0!", "success")

    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/update-races", methods=["POST"])
@admin_required
def update_races():
    """Update race data from F1 API"""
    success = race_data_manager.update_races_from_api()

    if success:
        flash("Race data updated successfully from F1 API!", "success")
    else:
        flash("Failed to update race data from F1 API", "error")

    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/update-drivers", methods=["POST"])
@admin_required
def update_drivers():
    """Update driver data from F1 API"""
    success = race_data_manager.update_drivers_from_api()

    if success:
        flash("Driver data updated successfully from F1 API!", "success")
    else:
        flash("Failed to update driver data from F1 API", "error")

    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/resolve-race", methods=["GET", "POST"])
@admin_required
def resolve_race():
    """Resolve a race and award points to users"""
    from ..betting_manager import betting_manager

    if request.method == "POST":
        race_id = request.form.get("race_id")
        driver_1 = request.form.get("driver_1")
        driver_2 = request.form.get("driver_2")
        driver_3 = request.form.get("driver_3")

        if not all([race_id, driver_1, driver_2, driver_3]):
            flash("Please fill in all fields", "error")
            return redirect(url_for("admin.resolve_race"))

        actual_results = [driver_1, driver_2, driver_3]

        # Resolve the race
        points_summary = betting_manager.resolve_race(race_id, actual_results)

        if points_summary:
            # Update user scores
            for username, points in points_summary.items():
                betting_manager.update_user_score(username, points, race_id)

            flash(
                f"Race resolved! Points awarded to {len(points_summary)} users",
                "success",
            )
            return redirect(url_for("admin.admin_dashboard"))
        else:
            flash("No bets to resolve or error resolving race", "warning")
            return redirect(url_for("admin.admin_dashboard"))

    # GET request - show form
    races = race_data_manager.get_all_races()
    drivers = betting_manager.get_available_drivers_for_race(
        ""
    )  # Get any race's drivers

    return render_template("admin/resolve_race.html", races=races, drivers=drivers)


@admin_bp.route("/cancel-race", methods=["POST"])
@admin_bp.route("/cancel-race/<race_id>", methods=["POST"])
@admin_required
def cancel_race(race_id=None):
    """Mark a race as canceled"""
    # Get race_id from form if not in URL
    if not race_id:
        race_id = request.form.get("race_id")

    if not race_id:
        flash("No race selected", "error")
        return redirect(url_for("admin.admin_dashboard"))

    # Get current canceled races
    canceled_ids = race_data_manager.get_canceled_race_ids()

    # Add the race to canceled list if not already there
    if race_id not in canceled_ids:
        canceled_ids.append(race_id)
        success = race_data_manager.set_canceled_race_ids(canceled_ids)

        if success:
            flash(f"Race {race_id} marked as canceled!", "success")
        else:
            flash(f"Failed to mark race {race_id} as canceled", "error")
    else:
        flash(f"Race {race_id} is already marked as canceled", "info")

    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/uncancel-race", methods=["POST"])
@admin_bp.route("/uncancel-race/<race_id>", methods=["POST"])
@admin_required
def uncancel_race(race_id=None):
    """Remove canceled status from a race"""
    # Get race_id from form if not in URL
    if not race_id:
        race_id = request.form.get("race_id")

    if not race_id:
        flash("No race selected", "error")
        return redirect(url_for("admin.admin_dashboard"))

    # Get current canceled races
    canceled_ids = race_data_manager.get_canceled_race_ids()

    # Remove the race from canceled list if present
    if race_id in canceled_ids:
        canceled_ids.remove(race_id)
        success = race_data_manager.set_canceled_race_ids(canceled_ids)

        if success:
            flash(f"Race {race_id} marked as active!", "success")
        else:
            flash(f"Failed to mark race {race_id} as active", "error")
    else:
        flash(f"Race {race_id} is not marked as canceled", "info")

    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/clear-logs", methods=["POST"])
@admin_required
def clear_logs():
    """Clear the application log file"""
    from flask import current_app

    try:
        log_file = (
            os.path.join(current_app.instance_path, "logs", "app.log")
            if current_app.instance_path
            else "logs/app.log"
        )

        if os.path.exists(log_file):
            # Clear the log file by opening in write mode
            with open(log_file, "w") as f:
                f.write("Log file cleared\n")

            current_app.logger.info("Log file cleared by admin")
            flash("Log file cleared successfully!", "success")
        else:
            flash("No log file found to clear", "info")

    except Exception as e:
        current_app.logger.error(f"Error clearing logs: {e}")
        flash("Error clearing log file", "error")

    return redirect(url_for("admin.admin_dashboard"))


def _count_admins(users):
    """Helper function to count admin users"""
    return sum(1 for user in users.values() if user.get("is_admin", False))
