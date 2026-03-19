from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from ..utils import load_users, save_users, hash_password, verify_password
from ..decorators import login_required

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Handle the main index route - shows welcome page or user dashboard"""
    if "username" in session:
        # Show user dashboard with admin links if applicable
        users = load_users()
        return render_template(
            "dashboard.html",
            username=session["username"],
            is_admin=session.get("is_admin", False),
            users=users,
        )
    return render_template("index.html")


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
