from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from ..auth_decorators import login_required
from ..core import config
from ..services.user_service import user_service

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login."""
    user_service.ensure_first_admin()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        users = user_service.load_all()

        if username in users and user_service.verify_password(users[username]["password"], password):
            session["username"] = username
            session["is_admin"] = users[username].get("is_admin", False)
            session.permanent = bool(request.form.get("remember_me"))

            # Migrate legacy plaintext passwords
            if not users[username]["password"].startswith("pbkdf2_sha256$"):
                user_service.migrate_password(username, password)
            else:
                user_service.record_login(username)

            flash("Login successful!", "success")
            return redirect(url_for("main.index"))

        flash("Invalid username or password", "error")
        return redirect(url_for("main.index"))

    return redirect(url_for("main.index"))


@login_required
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Handle user registration."""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        reg_password = request.form.get("registration_password")

        users = user_service.load_all()
        is_first = len(users) == 0

        if not username or not password:
            flash("Username and password are required", "error")
        elif not is_first and reg_password != config.registration_password():
            flash("Invalid registration password", "error")
        elif username in users:
            flash("Username already exists", "error")
        else:
            user_service.create(username, password, is_admin=False)
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("main.index"))

    return render_template(
        "auth/register.html", require_registration_password=len(user_service.load_all()) > 0
    )


@auth_bp.route("/logout")
def logout():
    """Handle user logout."""
    session.pop("username", None)
    session.pop("is_admin", None)
    flash("You have been logged out", "info")
    return redirect(url_for("main.index"))
