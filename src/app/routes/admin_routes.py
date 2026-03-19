from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from ..utils import load_users, save_users
from ..decorators import admin_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@admin_required
def admin_dashboard():
    """Admin dashboard with system statistics"""
    users = load_users()
    return render_template("admin/dashboard.html", users=users)


@admin_bp.route("/users")
@admin_required
def manage_users():
    """User management page"""
    users = load_users()
    return render_template("admin/users.html", users=users)


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

    return redirect(url_for("admin.manage_users"))


@admin_bp.route("/users/<username>/demote", methods=["POST"])
@admin_required
def demote_user(username):
    """Demote admin user to regular user"""
    users = load_users()

    if username in users:
        users[username]["is_admin"] = False
        save_users(users)
        flash(f"User {username} demoted from admin", "success")
    else:
        flash(f"User {username} not found", "error")

    return redirect(url_for("admin.manage_users"))
