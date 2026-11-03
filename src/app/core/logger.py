"""
Unified logging for the entire application.

Usage:
    from .core.logger import get_logger
    logger = get_logger(__name__)

    logger.info("Bet placed: %s on %s", username, race_id)

Call setup_logging() once at app startup to configure the root logger
with file + console handlers. All named loggers propagate to root.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional

_LOG_FILE_PATH: Optional[str] = None


def get_logger(name: str = None) -> logging.Logger:
    """Return a named logger. Configure handlers via setup_logging()."""
    return logging.getLogger(name or __name__)


def setup_logging(log_dir: str, level: str = None) -> str:
    """
    Configure the root logger with a rotating file handler and a console
    handler. Idempotent — safe to call multiple times.

    Args:
        log_dir: Directory for the log file.
        level: Log level name (DEBUG, INFO, WARNING, ERROR). Defaults to
               LOG_LEVEL env var, then INFO.

    Returns:
        The absolute path of the log file.
    """
    global _LOG_FILE_PATH

    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app.log")
    _LOG_FILE_PATH = log_file

    log_level = getattr(logging, (level or os.environ.get("LOG_LEVEL", "INFO")).upper(), logging.INFO)

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    root = logging.getLogger()
    root.setLevel(log_level)

    # Avoid duplicate handlers on re-configuration
    for h in root.handlers[:]:
        root.removeHandler(h)
        h.close()

    file_handler = RotatingFileHandler(log_file, maxBytes=1024 * 1024, backupCount=5)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    get_logger(__name__).info("Logging configured — level=%s, file=%s", logging.getLevelName(log_level), log_file)
    return log_file


def get_log_file_path() -> Optional[str]:
    """Return the log file path set by setup_logging(), or None if not configured."""
    return _LOG_FILE_PATH
