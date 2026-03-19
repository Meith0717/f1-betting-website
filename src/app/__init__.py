from flask import Flask


def create_app():
    app = Flask(__name__)

    # Configure secret key for session
    app.config["SECRET_KEY"] = "dev-key"

    # Import and register blueprints from routes package
    from .routes import main_bp, auth_bp, admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)

    return app
