from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from ..utils import load_users, save_users
from ..decorators import admin_required
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
    users = load_users()
    # Get registration password from environment or default
    registration_password = get_registration_password()
    
    # Calculate total points
    total_points = sum(user.get('score', 0) for user in users.values())
    
    # Create sorted users list for leaderboard
    sorted_users = sorted(users.items(), key=lambda x: x[1].get('score', 0), reverse=True)
    
    return render_template(
        "admin/dashboard.html",
        users=users, 
        registration_password=registration_password,
        total_points=total_points,
        sorted_users=sorted_users
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

def _count_admins(users):
    """Helper function to count admin users"""
    return sum(1 for user in users.values() if user.get("is_admin", False))
