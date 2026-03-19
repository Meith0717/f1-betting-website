from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from ..utils import (
    load_users,
    save_users,
    ensure_first_admin,
    hash_password,
    verify_password,
)
from ..decorators import admin_required, login_required
from datetime import datetime

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login with session management"""
    # Ensure there's at least one admin user
    users = ensure_first_admin()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username in users and verify_password(users[username]["password"], password):
            session["username"] = username
            # Store admin status in session (ensure field exists)
            if "is_admin" not in users[username]:
                users[username]["is_admin"] = False
                save_users(users)
            session["is_admin"] = users[username]["is_admin"]
            # Update last login time
            users[username]["last_login"] = datetime.now().isoformat()

            # Migrate plaintext passwords to hashed on successful login
            password_needs_hashing = not users[username]["password"].startswith(
                "pbkdf2_sha256$"
            )
            if password_needs_hashing:
                users[username]["password"] = hash_password(password)

            # Always save after successful login
            save_users(users)

            flash("Login successful!", "success")
            return redirect(url_for("main.index"))
        else:
            flash("Invalid username or password", "error")

    return render_template("login.html")

@login_required
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Handle user registration"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            flash("Username and password are required", "error")
        else:
            users = load_users()
            if username in users:
                flash("Username already exists", "error")
            else:
                # Store user with robust structure and hashed password
                users[username] = {
                    "password": hash_password(password),
                    "email": f"{username}@example.com",  # Internal email, not shown to users
                    "created_at": datetime.now().isoformat(),
                    "last_login": None,
                    "is_admin": False,  # Default to non-admin (first user will be promoted by ensure_first_admin)
                }
                save_users(users)
                flash("Registration successful! Please login.", "success")
                return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth_bp.route("/logout")
def logout():
    """Handle user logout"""
    session.pop("username", None)
    session.pop("is_admin", None)
    flash("You have been logged out", "info")
    return redirect(url_for("main.index"))
