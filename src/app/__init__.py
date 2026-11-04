from flask import Flask
import os

from .core import config
from .core.logger import setup_logging


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = config.secret_key()
    # Cache-busting version for static assets — based on CSS file mtime,
    # so browsers refetch whenever the stylesheet actually changes
    css_path = os.path.join(app.root_path, "static", "css", "mobile-styles.css")
    app.config["STATIC_VERSION"] = str(int(os.path.getmtime(css_path))) if os.path.exists(css_path) else "1"

    log_dir = os.path.join(app.instance_path, "logs") if app.instance_path else "logs"
    setup_logging(log_dir)

    # Wire service dependencies (avoids circular imports at module level)
    from .race_data_manager import race_data_manager
    from .push_manager import push_manager
    from .services import bet_service, resolution_service, user_service, notification_service

    bet_service.set_race_manager(race_data_manager)
    resolution_service.set_dependencies(bet_service, user_service, race_data_manager)
    notification_service.set_push_manager(push_manager)

    # Import and register blueprints from routes package
    from .routes import (
        main_bp, auth_bp, admin_bp, betting_bp, notifications_bp, system_bp,
    )

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(betting_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(system_bp)

    # Custom Jinja filters
    @app.template_filter("date_fmt")
    def date_fmt(value, fmt="%d.%m.%Y"):
        """Format an ISO date string (YYYY-MM-DD) into a display format."""
        if not value:
            return ""
        from datetime import datetime
        try:
            return datetime.strptime(str(value)[:10], "%Y-%m-%d").strftime(fmt)
        except ValueError:
            return str(value)

    @app.template_filter("date_range")
    def date_range(start, end):
        """Format a date range: 'DD.MM - DD.MM.YYYY' from two ISO date strings."""
        if not start or not end:
            return ""
        from datetime import datetime
        try:
            s = datetime.strptime(str(start)[:10], "%Y-%m-%d")
            e = datetime.strptime(str(end)[:10], "%Y-%m-%d")
            if s.year == e.year and s.month == e.month:
                return f"{s.strftime('%d.%m')} - {e.strftime('%d.%m.%Y')}"
            return f"{s.strftime('%d.%m.%Y')} - {e.strftime('%d.%m.%Y')}"
        except ValueError:
            return f"{start} - {end}"

    # Start the event manager for time-based notifications
    from .event_manager import event_manager

    event_manager.start()
    event_manager.schedule_all_race_notifications()

    return app
