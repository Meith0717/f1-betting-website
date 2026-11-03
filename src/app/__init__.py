from flask import Flask
import secrets
import os

from .core.logger import setup_logging


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = secrets.token_hex(32)

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

    # Start the event manager for time-based notifications
    from .event_manager import event_manager

    event_manager.start()
    event_manager.schedule_all_race_notifications()

    return app
