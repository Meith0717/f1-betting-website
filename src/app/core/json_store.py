"""
Atomic JSON file storage with automatic backup and restore.

Eliminates the duplicated backup/restore pattern that was previously
copy-pasted across save_bets(), save_users(), and save_subscriptions().
"""

import json
import os
import tempfile
import shutil
from typing import Any, Dict, Optional

from .logger import get_logger

logger = get_logger(__name__)


class JsonStore:
    """Thread-safe-ish JSON file store with atomic writes and backup/restore."""

    def __init__(self, filepath: str, default: Optional[Dict] = None):
        self.filepath = filepath
        self.default = default if default is not None else {}
        self._ensure_file()

    def _ensure_file(self) -> None:
        """Create the file with default content if it doesn't exist."""
        if os.path.exists(self.filepath):
            return
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        self._atomic_write(self.default)
        try:
            os.chmod(self.filepath, 0o600)
        except Exception:
            pass

    def load(self) -> Dict[str, Any]:
        """Load and return the full JSON content. Returns default on error."""
        try:
            if not os.path.exists(self.filepath):
                self._ensure_file()
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Merge defaults for any missing top-level keys
            for key, value in self.default.items():
                data.setdefault(key, value)
            return data
        except (json.JSONDecodeError, IOError) as e:
            logger.error("Error loading %s: %s", self.filepath, e)
            return dict(self.default)

    def save(self, data: Dict[str, Any]) -> None:
        """
        Save data with backup-and-restore safety.

        Writes to a temp file first, backs up the existing file,
        then atomically replaces it. On failure, restores from backup.
        """
        backup_file = self.filepath + ".bak"
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)

            # Create backup of existing file
            if os.path.exists(self.filepath):
                shutil.copy2(self.filepath, backup_file)

            self._atomic_write(data)

            # Remove backup on success
            if os.path.exists(backup_file):
                os.remove(backup_file)

        except Exception as e:
            logger.error("Error saving %s: %s", self.filepath, e)
            # Restore from backup
            if os.path.exists(backup_file):
                try:
                    shutil.move(backup_file, self.filepath)
                    logger.error("Restored from backup after save failure")
                except Exception as restore_error:
                    logger.error(
                        "Failed to restore backup: %s", restore_error
                    )
            raise

    def _atomic_write(self, data: Dict[str, Any]) -> None:
        """Write JSON atomically using a temp file + rename."""
        data_dir = os.path.dirname(self.filepath)
        fd, tmp_path = tempfile.mkstemp(dir=data_dir, prefix=".tmp_")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            try:
                os.chmod(tmp_path, 0o600)
            except Exception:
                pass
            shutil.move(tmp_path, self.filepath)
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise
