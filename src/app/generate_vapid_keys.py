#!/usr/bin/env python3
"""
Generate VAPID keys for Web Push notifications.
Run this once to generate your keys, then save them in .env or config.

Usage:
    python app/generate_vapid_keys.py

This will create .env and vapid_keys.json in the project root with VAPID keys.
"""

import os
import json
import base64
import sys
from pathlib import Path

try:
    from py_vapid import Vapid
    from cryptography.hazmat.primitives import serialization
except ImportError:
    print("❌ Error: Dependencies missing. Run: pip install py-vapid cryptography")
    sys.exit(1)


def generate_keys():
    """Generate VAPID keys and save to .env and vapid_keys.json"""
    # Get project root (grandparent of app directory)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent

    env_file = project_root / ".env"
    vapid_json = project_root / "vapid_keys.json"

    # Check if keys already exist
    if env_file.exists():
        with open(env_file, "r") as f:
            content = f.read()
            if "VAPID_PUBLIC_KEY=" in content and "VAPID_PRIVATE_KEY=" in content:
                print("✅ VAPID keys already exist in .env")
                return True

    print("🔑 Generating new VAPID keys...")

    # Generate Keys
    vapid = Vapid()
    vapid.generate_keys()

    # Extract Public Key (Uncompressed Point format)
    public_key_bytes = vapid.public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    vapid_public_str = (
        base64.urlsafe_b64encode(public_key_bytes).decode("utf-8").strip("=")
    )

    # Extract Private Key (DER format)
    private_key_bytes = vapid.private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    vapid_private_str = (
        base64.urlsafe_b64encode(private_key_bytes).decode("utf-8").strip("=")
    )

    claim_email = "mailto:f1betting@icloud.com"

    # Update .env
    new_content = f"""# VAPID Keys for Web Push Notifications
VAPID_PUBLIC_KEY={vapid_public_str}
VAPID_PRIVATE_KEY={vapid_private_str}
VAPID_CLAIM_EMAIL={claim_email}

"""

    if env_file.exists():
        with open(env_file, "r") as f:
            content = f.read()
        if "VAPID_PUBLIC_KEY=" not in content:
            with open(env_file, "a") as f:
                f.write(new_content)
    else:
        with open(env_file, "w") as f:
            f.write(new_content)

    # Save vapid_keys.json for reference
    with open(vapid_json, "w") as f:
        json.dump(
            {
                "public_key": vapid_public_str,
                "private_key": vapid_private_str,
                "claim_email": claim_email,
            },
            f,
            indent=2,
        )

    print(f"✅ .env created: {env_file.resolve()}")
    print(f"✅ vapid_keys.json created: {vapid_json.resolve()}")
    print()
    print(f"Public Key: {vapid_public_str}")
    return True


if __name__ == "__main__":
    try:
        generate_keys()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
