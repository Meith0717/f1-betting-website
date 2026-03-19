from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from ..utils import load_users, save_users
from ..decorators import admin_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@admin_required
def admin_dashboard():
    """Admin dashboard with system statistics"""
    users = load_users()
    # Get registration password from environment or default
    registration_password = os.environ.get("REGISTRATION_PASSWORD", "f1betting2024")
    return render_template(
        "admin/dashboard.html", users=users, registration_password=registration_password
    )


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

    admin_count = _count_admins(users)

    if admin_count <= 1:
        flash(
            "Cannot demote the last admin user. At least one admin must remain.",
            "error",
        )
    else:
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

    is_admin_user = users[username].get("is_admin", False)
    admin_count = _count_admins(users)

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


def _count_admins(users):
    """Helper function to count admin users"""
    return sum(1 for user in users.values() if user.get("is_admin", False))
