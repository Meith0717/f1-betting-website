"""
Web Push Notification API Routes for F1 Betting Platform.

Routes:
- POST /api/save-subscription - Save push subscription for a user
- POST /api/remove-subscription - Remove push subscription for a user
- POST /api/test-notification - Test sending a notification (admin only)
- POST /api/send-all - Send notification to all users (admin only)
"""

from flask import (
    Blueprint,
    request,
    jsonify,
    session,
    current_app,
    flash,
    redirect,
    url_for,
)
from ..auth_decorators import login_required, admin_required
from ..push_manager import push_manager
from ..auth_utils import load_users
import os
import json

# Create blueprint
notifications_bp = Blueprint("notifications", __name__, url_prefix="/api")


@notifications_bp.route("/vapid-public-key", methods=["GET"])
def get_vapid_public_key():
    """
    Get the VAPID public key for frontend use.
    This is needed for the browser to subscribe to push notifications.
    """
    try:
        public_key, _, __ = _get_vapid_keys()

        if not public_key:
            current_app.logger.error("VAPID public key not configured")
            return (
                jsonify({"success": False, "error": "VAPID keys not configured"}),
                500,
            )

        return jsonify({"success": True, "vapidPublicKey": public_key}), 200

    except Exception as e:
        current_app.logger.error(f"Error getting VAPID public key: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@notifications_bp.route("/save-subscription", methods=["POST"])
@login_required
def save_subscription():
    """
    Save a push subscription for the current user.

    Request body:
    {
        "subscription": {
            "endpoint": "https://...",
            "keys": {
                "p256dh": "...",
                "auth": "..."
            }
        }
    }

    Note: The username is taken from the session, not the request body.
    """
    try:
        current_app.logger.debug("Save subscription request received")

        # Get username from session
        username = session.get("username")
        if not username:
            current_app.logger.warning("No username in session for subscription save")
            return jsonify({"success": False, "error": "Not logged in"}), 401

        # Get subscription data from request
        data = request.get_json()
        if not data or "subscription" not in data:
            current_app.logger.warning("Missing subscription data in request")
            return (
                jsonify({"success": False, "error": "Missing subscription data"}),
                400,
            )

        subscription = data["subscription"]

        # Validate subscription structure
        if (
            not subscription
            or "endpoint" not in subscription
            or "keys" not in subscription
        ):
            current_app.logger.warning("Invalid subscription structure")
            return (
                jsonify({"success": False, "error": "Invalid subscription structure"}),
                400,
            )

        # Extract keys
        keys = subscription.get("keys", {})
        endpoint = subscription.get("endpoint")
        p256dh = keys.get("p256dh")
        auth = keys.get("auth")

        if not all([endpoint, p256dh, auth]):
            current_app.logger.warning("Missing required subscription fields")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Missing required fields: endpoint, p256dh, auth",
                    }
                ),
                400,
            )

        # Save subscription using push_manager
        success = push_manager.add_subscription(username, endpoint, p256dh, auth)

        if success:
            current_app.logger.info(f"Push subscription saved for user: {username}")
            return (
                jsonify(
                    {
                        "success": True,
                        "message": "Subscription saved successfully",
                        "endpoint": endpoint,
                    }
                ),
                200,
            )
        else:
            current_app.logger.error(
                f"Failed to save subscription for user: {username}"
            )
            return (
                jsonify({"success": False, "error": "Failed to save subscription"}),
                500,
            )

    except Exception as e:
        current_app.logger.error(f"Error saving subscription: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@notifications_bp.route("/remove-subscription", methods=["POST"])
@login_required
def remove_subscription():
    """
    Remove a push subscription for the current user.

    Request body:
    {
        "endpoint": "https://..."
    }
    """
    try:
        current_app.logger.debug("Remove subscription request received")

        # Get username from session
        username = session.get("username")
        if not username:
            current_app.logger.warning(
                "No username in session for subscription removal"
            )
            return jsonify({"success": False, "error": "Not logged in"}), 401

        # Get endpoint from request
        data = request.get_json()
        if not data or "endpoint" not in data:
            current_app.logger.warning("Missing endpoint in removal request")
            return jsonify({"success": False, "error": "Missing endpoint"}), 400

        endpoint = data["endpoint"]

        # Remove subscription using push_manager
        success = push_manager.remove_subscription(username, endpoint)

        if success:
            current_app.logger.info(f"Push subscription removed for user: {username}")
            return (
                jsonify(
                    {
                        "success": True,
                        "message": "Subscription removed successfully",
                        "endpoint": endpoint,
                    }
                ),
                200,
            )
        else:
            current_app.logger.warning(
                f"Failed to remove subscription for user: {username}"
            )
            return (
                jsonify({"success": False, "error": "Failed to remove subscription"}),
                404,
            )

    except Exception as e:
        current_app.logger.error(f"Error removing subscription: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@notifications_bp.route("/my-subscriptions", methods=["GET"])
@login_required
def get_my_subscriptions():
    """
    Get all push subscriptions for the current user.
    """
    try:
        username = session.get("username")
        if not username:
            return jsonify({"success": False, "error": "Not logged in"}), 401

        subscriptions = push_manager.get_user_subscriptions(username)

        # Mask sensitive information in logs
        current_app.logger.debug(
            f" retrieved {len(subscriptions)} subscriptions for user: {username}"
        )

        return jsonify({"success": True, "subscriptions": subscriptions}), 200

    except Exception as e:
        current_app.logger.error(f"Error getting subscriptions: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@notifications_bp.route("/remove-all-subscriptions", methods=["POST"])
@login_required
def remove_all_subscriptions():
    """
    Remove all push subscriptions for the current user.
    """
    try:
        username = session.get("username")
        if not username:
            return jsonify({"success": False, "error": "Not logged in"}), 401

        count = push_manager.remove_all_subscriptions(username)

        current_app.logger.info(
            f"Removed {count} push subscriptions for user: {username}"
        )

        return (
            jsonify(
                {
                    "success": True,
                    "message": f"Removed {count} subscriptions",
                    "count": count,
                }
            ),
            200,
        )

    except Exception as e:
        current_app.logger.error(
            f"Error removing all subscriptions: {e}", exc_info=True
        )
        return jsonify({"success": False, "error": str(e)}), 500


def _get_vapid_keys():
    """
    Get VAPID keys from environment variables.

    Returns:
        tuple: (public_key, private_key, claim_email) or (None, None, None)
    """
    import os

    public_key = os.environ.get("VAPID_PUBLIC_KEY")
    private_key = os.environ.get("VAPID_PRIVATE_KEY")
    claim_email = os.environ.get("VAPID_CLAIM_EMAIL", "mailto:f1betting@icloud.com")

    # If public/private keys are not in environment, try to read from .env file
    if not public_key or not private_key:
        try:
            # Look in multiple possible locations for .env file
            possible_paths = [
                # Project root (where generate_vapid_keys.py saves it)
                os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".env"),
                # src root
                os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"),
                # Direct parent
                os.path.join(os.path.dirname(__file__), ".env"),
                # Common locations
                os.path.join(os.path.dirname(__file__), "..", ".env"),
            ]

            for env_path in possible_paths:
                if os.path.exists(env_path):
                    with open(env_path, "r") as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith("VAPID_PUBLIC_KEY="):
                                public_key = line.split("=", 1)[1].strip()
                            elif line.startswith("VAPID_PRIVATE_KEY="):
                                private_key = line.split("=", 1)[1].strip()
                            elif line.startswith("VAPID_CLAIM_EMAIL="):
                                claim_email = line.split("=", 1)[1].strip()
                    if public_key and private_key:
                        current_app.logger.info(f"Loaded VAPID keys from {env_path}")
                        break
        except Exception as e:
            current_app.logger.warning(f"Could not read .env file: {e}")

    # Log what we found
    if public_key and private_key:
        current_app.logger.info("VAPID keys loaded successfully")
    else:
        current_app.logger.error(
            "VAPID keys NOT loaded - public_key: %s, private_key: %s",
            bool(public_key),
            bool(private_key),
        )

    return public_key, private_key, claim_email


def send_push_notification(username, title, message, data=None, url=None):
    """
    Send a push notification to a specific user.

    Args:
        username: The username to send to
        title: Notification title
        message: Notification body text
        data: Optional data dict to include in notification
        url: Optional URL to open when notification is clicked

    Returns:
        dict: {'success': bool, 'sent': int, 'failed': int, 'errors': list}
    """
    import pywebpush
    from pywebpush import webpush
    import json as json_module

    try:
        public_key, private_key, claim_email = _get_vapid_keys()

        if not public_key or not private_key:
            current_app.logger.error("VAPID keys not configured")
            return {
                "success": False,
                "error": "VAPID keys not configured",
                "sent": 0,
                "failed": 0,
            }

        # Get user's subscriptions
        subscriptions = push_manager.get_user_subscriptions(username)

        if not subscriptions:
            current_app.logger.warning(
                f"No push subscriptions found for user: {username}"
            )
            return {
                "success": True,
                "sent": 0,
                "failed": 0,
                "message": f"No subscriptions for {username}",
            }

        sent = 0
        failed = 0
        errors = []

        # Prepare notification payload
        payload = {
            "title": title,
            "body": message,
            "data": data or {},
            "url": url or "/",
        }

        # Send to each subscription
        for subscription in subscriptions:
            try:
                # Prepare subscription info for pywebpush
                subscription_info = {
                    "endpoint": subscription["endpoint"],
                    "keys": {
                        "p256dh": subscription["p256dh"],
                        "auth": subscription["auth"],
                    },
                }

                # Send push notification
                webpush(
                    subscription_info=subscription_info,
                    data=json_module.dumps(payload),
                    vapid_private_key=private_key,
                    vapid_claims={"sub": claim_email},
                    ttl=3600,  # Time to live in seconds (1 hour)
                )

                sent += 1
                current_app.logger.info(
                    f"Push notification sent to {username} at {subscription['endpoint']}"
                )

            except pywebpush.exceptions.HTTPNOTFOUND as e:
                # 404 - Subscription no longer valid, should be removed
                current_app.logger.warning(
                    f"Subscription expired for {username}: {subscription['endpoint']}"
                )
                # Remove this subscription
                push_manager.remove_subscription(username, subscription["endpoint"])
                failed += 1
                errors.append(
                    {
                        "endpoint": subscription["endpoint"],
                        "error": "Subscription expired (410 Gone)",
                        "action": "removed",
                    }
                )

            except pywebpush.exceptions.HTTPFORBIDDEN as e:
                # 403 - VAPID signature failed or invalid
                current_app.logger.error(f"VAPID signature error for {username}: {e}")
                failed += 1
                errors.append(
                    {
                        "endpoint": subscription["endpoint"],
                        "error": "VAPID signature error (403 Forbidden)",
                    }
                )

            except pywebpush.exceptions.HTTPSError as e:
                # Other HTTP errors (500, etc.)
                current_app.logger.error(f"HTTP error sending to {username}: {e}")
                failed += 1
                errors.append(
                    {"endpoint": subscription["endpoint"], "error": f"HTTP error: {e}"}
                )

            except Exception as e:
                current_app.logger.error(f"Error sending push to {username}: {e}")
                failed += 1
                errors.append({"endpoint": subscription["endpoint"], "error": str(e)})

        success = failed == 0

        return {
            "success": success,
            "sent": sent,
            "failed": failed,
            "errors": errors,
            "total_subscriptions": len(subscriptions),
        }

    except Exception as e:
        current_app.logger.error(
            f"Fatal error in send_push_notification: {e}", exc_info=True
        )
        return {"success": False, "error": str(e), "sent": 0, "failed": 0}


def send_push_notification_to_all(title, message, data=None, url=None):
    """
    Send push notification to all users with active subscriptions.

    Args:
        title: Notification title
        message: Notification body text
        data: Optional data dict
        url: Optional URL to open when clicked

    Returns:
        dict: {'success': bool, 'sent': int, 'failed': int, 'errors': list}
    """
    all_subscriptions = push_manager.get_all_subscriptions()

    sent_total = 0
    failed_total = 0
    errors_total = []

    for username, subscriptions in all_subscriptions.items():
        result = send_push_notification(username, title, message, data, url)
        sent_total += result.get("sent", 0)
        failed_total += result.get("failed", 0)
        errors_total.extend(result.get("errors", []))

    return {
        "success": failed_total == 0,
        "sent": sent_total,
        "failed": failed_total,
        "errors": errors_total,
        "total_users": len(all_subscriptions),
        "total_subscriptions": sum(len(s) for s in all_subscriptions.values()),
    }


# ============================================
# Admin Routes for Notification Management
# ============================================


@notifications_bp.route("/admin/send-test", methods=["POST"])
@admin_required
def admin_send_test():
    """
    Admin endpoint to send a test notification to a specific user.
    """
    try:
        username = request.form.get("username") or request.json.get("username")
        title = request.form.get("title") or request.json.get(
            "title", "Test Notification"
        )
        message = request.form.get("message") or request.json.get(
            "message", "This is a test push notification"
        )

        if not username:
            flash("Please provide a username", "error")
            return redirect(url_for("admin.admin_dashboard"))

        # Check if user exists
        users = load_users()
        if username not in users:
            flash(f'User "{username}" not found', "error")
            return redirect(url_for("admin.admin_dashboard"))

        result = send_push_notification(username, title, message)

        if result["success"] or result["sent"] > 0:
            flash(
                f"Test notification sent to {username}! Sent: {result['sent']}, Failed: {result['failed']}",
                "success",
            )
        else:
            flash(f"Failed to send: {result.get('error', 'Unknown error')}", "error")

        return redirect(url_for("admin.admin_dashboard"))

    except Exception as e:
        current_app.logger.error(f"Error sending test notification: {e}")
        flash("Error sending test notification", "error")
        return redirect(url_for("admin.admin_dashboard"))


@notifications_bp.route("/admin/send-all", methods=["POST"])
@admin_required
def admin_send_to_all():
    """
    Admin endpoint to send a notification to all users.
    """
    try:
        title = request.form.get("title") or request.json.get(
            "title", "Important Update"
        )
        message = request.form.get("message") or request.json.get(
            "message", "Check out the latest F1 news!"
        )

        result = send_push_notification_to_all(title, message)

        if result["success"] or result["sent"] > 0:
            flash(
                f"Notification sent to {result['total_users']} users! "
                f"Sent: {result['sent']}, Failed: {result['failed']}",
                "success",
            )
        else:
            flash(
                f"No notifications sent: {result.get('error', 'No subscribers or error')}",
                "warning",
            )

        return redirect(url_for("admin.admin_dashboard"))

    except Exception as e:
        current_app.logger.error(f"Error sending notification to all: {e}")
        flash("Error sending notification to all users", "error")
        return redirect(url_for("admin.admin_dashboard"))


@notifications_bp.route("/admin/subscriptions/count", methods=["GET"])
@admin_required
def admin_subscription_count():
    """
    Admin endpoint to get subscription statistics.
    """
    try:
        count = push_manager.count_subscriptions()
        all_subs = push_manager.get_all_subscriptions()

        return (
            jsonify(
                {
                    "success": True,
                    "total_subscriptions": count,
                    "users_with_subscriptions": len(all_subs),
                    "users_per_subscription": {k: len(v) for k, v in all_subs.items()},
                }
            ),
            200,
        )
    except Exception as e:
        current_app.logger.error(f"Error getting subscription count: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
