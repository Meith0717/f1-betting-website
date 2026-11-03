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

        from .services.user_service import user_service

        user_data = user_service.get(session["username"]) or {}
        if not user_data.get("is_admin", False):
            flash("Admin access required", "error")
            return redirect(url_for("main.index"))
        return f(*args, **kwargs)

    return decorated
