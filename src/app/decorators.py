from flask import flash, redirect, url_for, session
from functools import wraps


def login_required(f):
    """
    Decorator to require login for protected routes.

    Usage:
        @login_required
        def protected_route():
            # Only accessible to logged-in users
            pass
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import current_app
        
        current_app.logger.debug(f"Checking login requirement for route: {f.__name__}")
        
        # Check if user is logged in
        if "username" not in session:
            current_app.logger.warning(f"Unauthorized access attempt to {f.__name__} - no session")
            flash("Please login first", "error")
            return redirect(url_for("auth.login"))

        current_app.logger.debug(f"User {session['username']} authorized for {f.__name__}")
        return f(*args, **kwargs)

    return decorated_function


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
        from flask import current_app
        
        current_app.logger.debug(f"Checking admin requirement for route: {f.__name__}")
        
        # Check if user is logged in
        if "username" not in session:
            current_app.logger.warning(f"Unauthorized admin access attempt to {f.__name__} - no session")
            flash("Please login first", "error")
            return redirect(url_for("auth.login"))

        # Import here to avoid circular imports
        from .utils import load_users

        users = load_users()
        user_data = users.get(session["username"], {})
        
        current_app.logger.debug(f"User {session['username']} admin status: {user_data.get('is_admin', False)}")

        # Check if user is admin
        if not user_data.get("is_admin", False):
            current_app.logger.warning(f"Unauthorized admin access attempt by {session['username']} to {f.__name__}")
            flash("Admin access required", "error")
            return redirect(url_for("main.index"))

        current_app.logger.debug(f"Admin {session['username']} authorized for {f.__name__}")
        return f(*args, **kwargs)

    return decorated_function
