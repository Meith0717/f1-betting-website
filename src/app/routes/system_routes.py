"""
System routes — service worker and debug endpoint.

Extracted from the app factory (__init__.py) so all routes live in blueprints.
"""

import os
import sys
import platform
import importlib.metadata
from flask import Blueprint, jsonify, send_from_directory

from ..core.logger import get_logger

logger = get_logger(__name__)

system_bp = Blueprint("system", __name__)


@system_bp.route("/sw.js")
def serve_service_worker():
    """Serve the service worker from static folder at root path for push scope '/'."""
    from flask import current_app
    return send_from_directory(
        os.path.join(current_app.root_path, "static"), "sw.js"
    )


@system_bp.route("/_debug")
def debug_info():
    """Debug endpoint showing application state."""
    from flask import current_app

    info = {
        "app_name": current_app.name,
        "python_version": sys.version,
        "flask_version": importlib.metadata.version("flask"),
        "platform": platform.platform(),
        "debug_mode": current_app.debug,
        "config": {
            "SECRET_KEY": "*****" if current_app.config["SECRET_KEY"] else None,
            "SESSION_COOKIE_NAME": current_app.config.get("SESSION_COOKIE_NAME"),
        },
        "registered_blueprints": list(current_app.blueprints.keys()),
        "routes": [str(rule) for rule in current_app.url_map.iter_rules()],
    }
    logger.debug("Debug endpoint accessed")
    return jsonify(info)
