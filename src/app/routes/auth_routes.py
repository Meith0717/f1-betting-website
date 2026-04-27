from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from ..auth_utils import (
    load_users,
    save_users,
    ensure_first_admin,
    hash_password,
    verify_password,
    get_registration_password,
)
from ..auth_decorators import admin_required, login_required
from datetime import datetime
import pytz
import os

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login with session management"""
    from flask import current_app

    current_app.logger.debug("Login route accessed")
    users = ensure_first_admin()
    current_app.logger.debug(f"Loaded {len(users)} users, ensuring first admin")

    if request.method == "POST":
        current_app.logger.debug("Login POST request received")
        username = request.form.get("username")
        password = request.form.get("password")

        current_app.logger.debug(f"Login attempt for username: {username}")

        if username in users and verify_password(users[username]["password"], password):
            current_app.logger.info(f"Successful login for user: {username}")
            # Set up session
            session["username"] = username
            session["is_admin"] = users[username].get("is_admin", False)

            # Update user data
            users[username]["last_login"] = datetime.now(pytz.UTC).isoformat()

            # Migrate plaintext passwords
            if not users[username]["password"].startswith("pbkdf2_sha256$"):
                current_app.logger.warning(
                    f"Migrating plaintext password for user: {username}"
                )
                users[username]["password"] = hash_password(password)

            save_users(users)
            flash("Login successful!", "success")
            return redirect(url_for("main.index"))
        else:
            current_app.logger.warning(f"Failed login attempt for username: {username}")
            flash("Invalid username or password", "error")

    current_app.logger.debug("Rendering login template")
    return render_template("auth/login.html")


@login_required
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Handle user registration"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        reg_password = request.form.get("registration_password")

        users = load_users()
        is_first_user = len(users) == 0

        # Validate inputs
        if not username or not password:
            flash("Username and password are required", "error")
        elif not is_first_user and not reg_password:
            flash("Registration password is required", "error")
        elif not is_first_user and reg_password != get_registration_password():
            flash("Invalid registration password", "error")
        elif username in users:
            flash("Username already exists", "error")
        else:
            # Create new user
            users[username] = {
                "password": hash_password(password),
                "score": 0,
                "created_at": datetime.now(pytz.UTC).isoformat(),
                "last_login": None,
                "is_admin": False,
            }
            save_users(users)
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("auth.login"))

    return render_template(
        "auth/register.html", require_registration_password=len(load_users()) > 0
    )


@auth_bp.route("/logout")
def logout():
    """Handle user logout"""
    session.pop("username", None)
    session.pop("is_admin", None)
    flash("You have been logged out", "info")
    return redirect(url_for("main.index"))
