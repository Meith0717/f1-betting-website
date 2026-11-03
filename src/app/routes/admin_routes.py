from flask import (
    Blueprint, render_template, request, redirect, url_for,
    session, flash, current_app,
)
from ..auth_utils import load_users, save_users, get_registration_password
from ..auth_decorators import admin_required
from ..race_data_manager import race_data_manager
from ..push_manager import push_manager
from ..services.user_service import user_service
import os
import secrets

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _log_file_path():
    return (
        os.path.join(current_app.instance_path, "logs", "app.log")
        if current_app.instance_path
        else "logs/app.log"
    )


def _read_log_entries(max_lines=50):
    path = _log_file_path()
    if not os.path.exists(path):
        return [], False
    try:
        with open(path, "r") as f:
            lines = f.readlines()
        return (lines[-max_lines:] if len(lines) > max_lines else lines)[::-1], True
    except Exception as e:
        current_app.logger.error(f"Error reading log file: {e}")
        return [f"Error reading log file: {e}"], True


@admin_bp.route("/")
@admin_required
def admin_dashboard():
    """Admin dashboard with system statistics."""
    current_app.logger.info("Admin dashboard accessed")

    users = load_users()
    log_entries, log_exists = _read_log_entries()

    return render_template(
        "admin/dashboard.html",
        users=users,
        registration_password=get_registration_password(),
        total_points=sum(u.get("score", 0) for u in users.values()),
        sorted_users=user_service.get_leaderboard(),
        races=race_data_manager.get_all_races(),
        canceled_race_ids=race_data_manager.get_canceled_race_ids(),
        log_entries=log_entries,
        log_file_exists=log_exists,
    )


@admin_bp.route("/users/<username>/promote", methods=["POST"])
@admin_required
def promote_user(username):
    """Promote a user to admin."""
    if user_service.exists(username):
        user_service.update(username, is_admin=True)
        flash(f"User {username} promoted to admin", "success")
    else:
        flash(f"User {username} not found", "error")
    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/users/<username>/demote", methods=["POST"])
@admin_required
def demote_user(username):
    """Demote an admin to regular user (cannot demote the last admin)."""
    if not user_service.exists(username):
        flash(f"User {username} not found", "error")
        return redirect(url_for("admin.admin_dashboard"))

    if user_service.count_admins() <= 1:
        flash("Cannot demote the last admin. At least one admin must remain.", "error")
    else:
        user_service.update(username, is_admin=False)
        flash(f"User {username} demoted from admin", "success")
    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/users/<username>/delete", methods=["POST"])
@admin_required
def delete_user(username):
    """Delete a user (cannot delete self or the last admin)."""
    if username == session.get("username"):
        flash("Cannot delete your own account", "error")
        return redirect(url_for("admin.admin_dashboard"))

    if not user_service.exists(username):
        flash(f"User {username} not found", "error")
        return redirect(url_for("admin.admin_dashboard"))

    is_admin = user_service.get(username).get("is_admin", False)
    if is_admin and user_service.count_admins() <= 1:
        flash("Cannot delete the last admin. At least one admin must remain.", "error")
    else:
        user_service.delete(username)
        flash(f"User {username} deleted successfully", "success")
    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/users/<username>/send-test-notification", methods=["POST"])
@admin_required
def send_test_notification(username):
    """Send a test push notification to a specific user."""
    import pywebpush
    import json as json_module

    if not user_service.exists(username):
        flash(f"User {username} not found", "error")
        return redirect(url_for("admin.admin_dashboard"))

    public_key = os.environ.get("VAPID_PUBLIC_KEY")
    private_key = os.environ.get("VAPID_PRIVATE_KEY")
    claim_email = os.environ.get("VAPID_CLAIM_EMAIL", "mailto:f1betting@icloud.com")

    if not public_key or not private_key:
        flash("Push notifications not configured (missing VAPID keys)", "error")
        return redirect(url_for("admin.admin_dashboard"))

    subscriptions = push_manager.get_user_subscriptions(username)
    if not subscriptions:
        flash(f"{username} has no active push subscriptions", "info")
        return redirect(url_for("admin.admin_dashboard"))

    payload = {
        "title": "Test Notification",
        "body": f"Hello {username}! This is a test notification from the admin.",
        "data": {"test": True, "from_admin": True},
        "url": "/",
    }

    sent = failed = 0
    errors = []
    for sub in subscriptions:
        try:
            pywebpush.webpush(
                subscription_info={
                    "endpoint": sub["endpoint"],
                    "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
                },
                data=json_module.dumps(payload),
                vapid_private_key=private_key,
                vapid_claims={"sub": claim_email},
            )
            sent += 1
        except Exception as e:
            failed += 1
            errors.append(str(e))

    if sent:
        flash(f"Test notification sent to {username} ({sent} device(s))", "success")
    else:
        flash(f"Failed: {errors[0] if errors else 'Unknown error'}", "error")

    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/change-registration-password", methods=["POST"])
@admin_required
def change_registration_password():
    """Generate a new random registration password."""
    new_password = secrets.token_urlsafe(16)
    os.environ["REGISTRATION_PASSWORD"] = new_password
    flash(f"Registration password changed to: {new_password}", "success")
    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/reset-all-points", methods=["POST"])
@admin_required
def reset_all_points():
    """Reset all user scores to 0."""
    user_service.reset_all_scores()
    flash("All user points have been reset to 0!", "success")
    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/update-races", methods=["POST"])
@admin_required
def update_races():
    """Update race data from F1 API."""
    if race_data_manager.update_races_from_api():
        flash("Race data updated successfully from F1 API!", "success")
    else:
        flash("Failed to update race data from F1 API", "error")
    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/update-drivers", methods=["POST"])
@admin_required
def update_drivers():
    """Update driver data from F1 API."""
    if race_data_manager.update_drivers_from_api():
        flash("Driver data updated successfully from F1 API!", "success")
    else:
        flash("Failed to update driver data from F1 API", "error")
    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/resolve-race", methods=["GET", "POST"])
@admin_required
def resolve_race():
    """Resolve a race manually and award points."""
    from ..betting_manager import betting_manager

    if request.method == "POST":
        race_id = request.form.get("race_id")
        drivers = [
            request.form.get("driver_1"),
            request.form.get("driver_2"),
            request.form.get("driver_3"),
        ]
        if not all([race_id] + drivers):
            flash("Please fill in all fields", "error")
            return redirect(url_for("admin.resolve_race"))

        summary = betting_manager.resolve_race(race_id, drivers)
        if summary:
            flash(f"Race resolved! Points awarded to {len(summary)} users", "success")
        else:
            flash("No bets to resolve or error resolving race", "warning")
        return redirect(url_for("admin.admin_dashboard"))

    return render_template(
        "admin/resolve_race.html",
        races=race_data_manager.get_all_races(),
        drivers=betting_manager.get_available_drivers_for_race(""),
    )


@admin_bp.route("/cancel-race", methods=["POST"])
@admin_bp.route("/cancel-race/<race_id>", methods=["POST"])
@admin_required
def cancel_race(race_id=None):
    """Mark a race as canceled."""
    race_id = race_id or request.form.get("race_id")
    if not race_id:
        flash("No race selected", "error")
        return redirect(url_for("admin.admin_dashboard"))

    if race_data_manager.cancel_race(race_id):
        flash(f"Race {race_id} marked as canceled!", "success")
    else:
        flash(f"Race {race_id} is already canceled or failed", "info")
    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/uncancel-race", methods=["POST"])
@admin_bp.route("/uncancel-race/<race_id>", methods=["POST"])
@admin_required
def uncancel_race(race_id=None):
    """Remove canceled status from a race."""
    race_id = race_id or request.form.get("race_id")
    if not race_id:
        flash("No race selected", "error")
        return redirect(url_for("admin.admin_dashboard"))

    if race_data_manager.uncancel_race(race_id):
        flash(f"Race {race_id} marked as active!", "success")
    else:
        flash(f"Race {race_id} is not canceled or failed", "info")
    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/clear-logs", methods=["POST"])
@admin_required
def clear_logs():
    """Clear the application log file."""
    try:
        path = _log_file_path()
        if os.path.exists(path):
            with open(path, "w") as f:
                f.write("Log file cleared\n")
            current_app.logger.info("Log file cleared by admin")
            flash("Log file cleared successfully!", "success")
        else:
            flash("No log file found to clear", "info")
    except Exception as e:
        current_app.logger.error(f"Error clearing logs: {e}")
        flash("Error clearing log file", "error")
    return redirect(url_for("admin.admin_dashboard"))
