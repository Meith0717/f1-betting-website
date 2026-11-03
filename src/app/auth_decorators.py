"""
Authentication decorators for route protection.
"""

from functools import wraps
from flask import flash, redirect, url_for, session


def login_required(f):
    """Require an active login session."""

    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            flash("Please login first", "error")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)

    return decorated


def admin_required(f):
    """Require an active admin session."""

    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            flash("Please login first", "error")
            return redirect(url_for("auth.login"))

        from .auth_utils import load_users

        user_data = load_users().get(session["username"], {})
        if not user_data.get("is_admin", False):
            flash("Admin access required", "error")
            return redirect(url_for("main.index"))
        return f(*args, **kwargs)

    return decorated
