from flask import (
    Blueprint, Response, render_template, request, redirect, url_for,
    session, flash,
)
from ..auth_decorators import admin_required
from ..core import config
from ..core.logger import get_logger, get_log_file_path, get_event_log_file_path
from ..race_data_manager import race_data_manager
from ..event_manager import event_manager
from ..push_manager import push_manager
from ..services.user_service import user_service
import os
import secrets
from datetime import datetime, timedelta

logger = get_logger(__name__)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


_EVENT_LABELS = [
    ("race_1h_before", "1h before race", "bell"),
    ("qualifying_start", "Qualifying start", "flag"),
    ("race_start", "Race start", "flag"),
    ("resolve_attempt", "Resolve attempt", "check"),
    ("weekend_overview", "Weekend overview", "calendar"),
    ("maintenance_job", "Maintenance job", "gear"),
    ("weekly_refresh", "Weekly refresh", "gear"),
]


def _relative(delta: timedelta) -> str:
    total = int(delta.total_seconds())
    if total <= 0:
        return "now"
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        return f"in {days}d {hours}h"
    if hours:
        return f"in {hours}h {minutes}min"
    return f"in {minutes}min"


def _event_display_entries():
    """Pending events enriched for mobile display: label, local time, relative."""
    from ..timezone_utils import timezone_utils

    now = timezone_utils.utc_now()
    entries = []
    for e in event_manager.list_events():
        eid = e["id"]
        label, icon = "Event", "clock"
        for prefix, lbl, ic in _EVENT_LABELS:
            if eid.startswith(prefix + "_"):
                label, icon = lbl, ic
                break
        trig = datetime.fromisoformat(e["trigger_time"])
        entries.append(
            {
                "id": eid,
                "label": label,
                "icon": icon,
                "trigger_local": trig.astimezone(timezone_utils.local_timezone).strftime(
                    "%a %d.%m %H:%M"
                ),
                "relative": _relative(trig - now),
            }
        )
    return entries


@admin_bp.route("/")
@admin_required
def admin_dashboard():
    """Admin dashboard with system statistics."""
    logger.info("Admin dashboard accessed")

    users = user_service.load_all()

    return render_template(
        "admin/dashboard.html",
        users=users,
        registration_password=config.registration_password(),
        total_points=sum(u.get("score", 0) for u in users.values()),
        sorted_users=user_service.get_leaderboard(),
        races=race_data_manager.get_all_races(),
        canceled_race_ids=race_data_manager.get_canceled_race_ids(),
        active_events=_event_display_entries(),
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
    if not user_service.exists(username):
        flash(f"User {username} not found", "error")
        return redirect(url_for("admin.admin_dashboard"))

    result = push_manager.send_to_user(
        username,
        "Test Notification",
        f"Hello {username}! This is a test notification from the admin.",
        data={"test": True, "from_admin": True},
    )

    if result.get("sent", 0) > 0:
        flash(f"Test notification sent to {username} ({result['sent']} device(s))", "success")
    else:
        flash(f"Failed: {result.get('error', 'No subscriptions or unknown error')}", "error")

    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/change-registration-password", methods=["POST"])
@admin_required
def change_registration_password():
    """Generate a new random registration password."""
    new_password = secrets.token_urlsafe(16)
    config.set_registration_password(new_password)
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


@admin_bp.route("/logs/<name>")
@admin_required
def view_log(name):
    """Serve a raw log file as text/plain so it can open in a new browser tab."""
    path = {
        "app": get_log_file_path(),
        "events": get_event_log_file_path(),
    }.get(name)
    if not path or not os.path.exists(path):
        flash("Log file not found", "error")
        return redirect(url_for("admin.admin_dashboard"))
    try:
        with open(path, "r") as f:
            content = f.read()
    except Exception as e:
        logger.error("Error reading log file %s: %s", path, e)
        flash("Error reading log file", "error")
        return redirect(url_for("admin.admin_dashboard"))
    return Response(content, mimetype="text/plain; charset=utf-8")


