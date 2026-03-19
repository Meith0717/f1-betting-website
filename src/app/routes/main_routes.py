from flask import Blueprint, render_template, session
from ..utils import load_users

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
