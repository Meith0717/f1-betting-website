from flask import Flask, jsonify, send_from_directory
import platform
import secrets
import sys
import os
from logging.handlers import RotatingFileHandler
import logging


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = secrets.token_hex(32)
    configure_logging(app)

    # Import and register blueprints from routes package
    from .routes import main_bp, auth_bp, admin_bp, betting_bp, notifications_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(betting_bp)
    app.register_blueprint(notifications_bp)

    # Start the event manager for time-based notifications
    from .event_manager import event_manager

    event_manager.start()
    event_manager.schedule_all_race_notifications()

    # Serve service worker from root for push notifications
    # This allows the SW to have scope '/' and work with all pages
    @app.route("/sw.js")
    def serve_service_worker():
        """Serve the service worker file from static folder at root path."""
        return send_from_directory(os.path.join(app.root_path, "static"), "sw.js")

    # Add debug endpoint
    @app.route("/_debug")
    def debug_info():
        """Debug endpoint to show application state."""
        debug_info = {
            "app_name": app.name,
            "python_version": sys.version,
            "flask_version": Flask.__version__,
            "platform": platform.platform(),
            "debug_mode": app.debug,
            "config": {
                "SECRET_KEY": "*****" if app.config["SECRET_KEY"] else None,
                "SESSION_COOKIE_NAME": app.config.get("SESSION_COOKIE_NAME"),
            },
            "registered_blueprints": list(app.blueprints.keys()),
            "routes": [str(rule) for rule in app.url_map.iter_rules()],
        }

        app.logger.debug("Debug endpoint accessed")
        return jsonify(debug_info)

    return app


def configure_logging(app):
    """Configure logging for the Flask application."""
    log_dir = os.path.join(app.instance_path, "logs") if app.instance_path else "logs"
    os.makedirs(log_dir, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "app.log"), maxBytes=1024 * 1024, backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    app.logger.handlers.clear()
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.DEBUG)

    app.logger.info("Logging configured successfully")
    app.logger.debug(f"Log directory: {log_dir}")
