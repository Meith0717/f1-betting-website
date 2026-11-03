"""
Centralized logger helper.

Provides a consistent way to get a logger that uses Flask's current_app.logger
when inside an app context, falling back to a standard logger otherwise.
"""

import logging


def get_logger(name: str = None) -> logging.Logger:
    """Get a logger, preferring Flask's app logger when available."""
    try:
        from flask import current_app

        return current_app.logger
    except RuntimeError:
        return logging.getLogger(name or __name__)
