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
import re
from logging.handlers import RotatingFileHandler
from typing import Optional

_LOG_FILE_PATH: Optional[str] = None
_EVENT_LOG_FILE_PATH: Optional[str] = None

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


class _AnsiStripFilter(logging.Filter):
    """Remove ANSI escape sequences from log records so log files stay plain text."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _ANSI_RE.sub("", str(record.msg))
        if record.args:
            record.args = tuple(
                _ANSI_RE.sub("", str(a)) if isinstance(a, str) else a
                for a in record.args
            )
        return True


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

    ansi_filter = _AnsiStripFilter()

    file_handler = RotatingFileHandler(log_file, maxBytes=1024 * 1024, backupCount=5)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(ansi_filter)
    root.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(ansi_filter)
    root.addHandler(console_handler)

    setup_event_logging(log_dir, level)

    get_logger(__name__).info("Logging configured — level=%s, file=%s", logging.getLevelName(log_level), log_file)
    return log_file


def setup_event_logging(log_dir: str, level: str = None) -> str:
    """
    Configure the dedicated "events" logger with its own rotating file
    (events.log). It does not propagate to root, so event activity is
    kept out of app.log. Idempotent — safe to call multiple times.

    Returns:
        The absolute path of the events log file.
    """
    global _EVENT_LOG_FILE_PATH

    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "events.log")
    _EVENT_LOG_FILE_PATH = log_file

    log_level = getattr(logging, (level or os.environ.get("LOG_LEVEL", "INFO")).upper(), logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    event_logger = logging.getLogger("events")
    event_logger.setLevel(log_level)
    event_logger.propagate = False  # keep events out of app.log

    for h in event_logger.handlers[:]:
        event_logger.removeHandler(h)
        h.close()

    handler = RotatingFileHandler(log_file, maxBytes=1024 * 1024, backupCount=5)
    handler.setLevel(log_level)
    handler.setFormatter(formatter)
    handler.addFilter(_AnsiStripFilter())
    event_logger.addHandler(handler)
    return log_file


def get_event_logger() -> logging.Logger:
    """Logger for event scheduling/firing — writes to events.log."""
    return logging.getLogger("events")


def get_log_file_path() -> Optional[str]:
    """Return the log file path set by setup_logging(), or None if not configured."""
    return _LOG_FILE_PATH


def get_event_log_file_path() -> Optional[str]:
    """Return the events log file path set by setup_event_logging(), or None."""
    return _EVENT_LOG_FILE_PATH
