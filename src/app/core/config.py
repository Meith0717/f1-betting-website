"""
Centralized configuration — all environment variable access in one place.

Eliminates scattered os.environ.get() calls across the codebase.
Falls back to reading the project-root .env file for VAPID keys.
"""

import os
from typing import Optional, Tuple

_PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..")


def _read_env_file() -> dict:
    """Read key=value pairs from the project-root .env file."""
    env_path = os.path.join(_PROJECT_ROOT, ".env")
    values = {}
    if not os.path.exists(env_path):
        return values
    try:
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, _, val = line.partition("=")
                    values[key.strip()] = val.strip()
    except Exception:
        pass
    return values


_ENV_FILE = _read_env_file()


def _get(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get a config value from environment, falling back to .env file."""
    return os.environ.get(key) or _ENV_FILE.get(key) or default


# -- VAPID (Web Push) --------------------------------------------------------

def vapid_public_key() -> Optional[str]:
    return _get("VAPID_PUBLIC_KEY")


def vapid_private_key() -> Optional[str]:
    return _get("VAPID_PRIVATE_KEY")


def vapid_claim_email() -> str:
    return _get("VAPID_CLAIM_EMAIL", "mailto:f1betting@icloud.com")


def vapid_keys() -> Tuple[Optional[str], Optional[str], str]:
    """Return (public_key, private_key, claim_email)."""
    return vapid_public_key(), vapid_private_key(), vapid_claim_email()


# -- Registration ------------------------------------------------------------

def registration_password() -> str:
    return _get("REGISTRATION_PASSWORD", "f1betting2024")


def set_registration_password(password: str) -> None:
    """Set the registration password (runtime only — env var)."""
    os.environ["REGISTRATION_PASSWORD"] = password
