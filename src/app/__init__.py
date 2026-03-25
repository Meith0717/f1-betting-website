from flask import Flask
import secrets
import logging
import os
from logging.handlers import RotatingFileHandler


def create_app():
    app = Flask(__name__)

    # Configure secret key for session
    app.config["SECRET_KEY"] = secrets.token_hex(32)

    # Configure logging
    configure_logging(app)

    # Import and register blueprints from routes package
    from .routes import main_bp, auth_bp, admin_bp, betting_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(betting_bp)

    # Add debug endpoint
    @app.route("/_debug")
    def debug_info():
        """Debug endpoint to show application state"""
        from flask import jsonify
        import platform
        import sys

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
    """Configure logging for the Flask application"""
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(app.instance_path, "logs") if app.instance_path else "logs"
    os.makedirs(log_dir, exist_ok=True)

    # Set up file handler with rotation
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "app.log"), maxBytes=1024 * 1024, backupCount=5  # 1MB
    )
    file_handler.setLevel(logging.DEBUG)

    # Set up console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    # Create formatter and add it to handlers
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Remove default handlers and add our own
    app.logger.handlers.clear()
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)

    # Set logger level
    app.logger.setLevel(logging.DEBUG)

    app.logger.info("Logging configured successfully")
    app.logger.debug(f"Log directory: {log_dir}")
