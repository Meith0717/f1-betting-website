from flask import flash, redirect, url_for, session
from functools import wraps


def admin_required(f):
    """
    Decorator to require admin access for protected routes.

    Usage:
        @admin_required
        def admin_route():
            # Only accessible to admin users
            pass
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is logged in
        if "username" not in session:
            flash("Please login first", "error")
            return redirect(url_for("main.login"))

        # Import here to avoid circular imports
        from .utils import load_users

        users = load_users()
        user_data = users.get(session["username"], {})

        # Check if user is admin
        if not user_data.get("is_admin", False):
            flash("Admin access required", "error")
            return redirect(url_for("main.index"))

        return f(*args, **kwargs)

    return decorated_function
