"""
Web Push Notification API routes.

Endpoints:
- GET  /api/vapid-public-key          — VAPID public key for frontend
- POST /api/save-subscription         — save push subscription (auth required)
- POST /api/remove-subscription       — remove push subscription (auth required)
- GET  /api/my-subscriptions          — list user's subscriptions (auth required)
- POST /api/remove-all-subscriptions  — remove all user subscriptions (auth required)
- POST /api/admin/send-test           — send test notification (admin)
- POST /api/admin/send-all            — send to all users (admin)
- GET  /api/admin/subscriptions/count — subscription stats (admin)
"""

from flask import Blueprint, request, jsonify, session, flash, redirect, url_for

from ..auth_decorators import login_required, admin_required
from ..core import config
from ..push_manager import push_manager
from ..services.user_service import user_service

notifications_bp = Blueprint("notifications", __name__, url_prefix="/api")


# -- Public / user endpoints -------------------------------------------------

@notifications_bp.route("/vapid-public-key", methods=["GET"])
def get_vapid_public_key():
    public = config.vapid_public_key()
    if not public:
        return jsonify({"success": False, "error": "VAPID keys not configured"}), 500
    return jsonify({"success": True, "vapidPublicKey": public}), 200


@notifications_bp.route("/save-subscription", methods=["POST"])
@login_required
def save_subscription():
    username = session.get("username")
    if not username:
        return jsonify({"success": False, "error": "Not logged in"}), 401

    data = request.get_json()
    sub = (data or {}).get("subscription", {})
    endpoint = sub.get("endpoint")
    keys = sub.get("keys", {})
    p256dh, auth = keys.get("p256dh"), keys.get("auth")

    if not all([endpoint, p256dh, auth]):
        return jsonify({"success": False, "error": "Missing required fields"}), 400

    if push_manager.add_subscription(username, endpoint, p256dh, auth):
        return jsonify({"success": True, "message": "Subscription saved", "endpoint": endpoint}), 200
    return jsonify({"success": False, "error": "Failed to save"}), 500


@notifications_bp.route("/remove-subscription", methods=["POST"])
@login_required
def remove_subscription():
    username = session.get("username")
    if not username:
        return jsonify({"success": False, "error": "Not logged in"}), 401

    endpoint = (request.get_json() or {}).get("endpoint")
    if not endpoint:
        return jsonify({"success": False, "error": "Missing endpoint"}), 400

    if push_manager.remove_subscription(username, endpoint):
        return jsonify({"success": True, "message": "Removed", "endpoint": endpoint}), 200
    return jsonify({"success": False, "error": "Not found"}), 404


@notifications_bp.route("/my-subscriptions", methods=["GET"])
@login_required
def get_my_subscriptions():
    username = session.get("username")
    if not username:
        return jsonify({"success": False, "error": "Not logged in"}), 401
    return jsonify({"success": True, "subscriptions": push_manager.get_user_subscriptions(username)}), 200


@notifications_bp.route("/remove-all-subscriptions", methods=["POST"])
@login_required
def remove_all_subscriptions():
    username = session.get("username")
    if not username:
        return jsonify({"success": False, "error": "Not logged in"}), 401
    count = push_manager.remove_all_subscriptions(username)
    return jsonify({"success": True, "message": f"Removed {count} subscriptions", "count": count}), 200


# -- Admin endpoints ---------------------------------------------------------

@notifications_bp.route("/admin/send-test", methods=["POST"])
@admin_required
def admin_send_test():
    data = request.form or (request.get_json(silent=True) or {})
    username = data.get("username")
    title = data.get("title", "Test Notification")
    message = data.get("message", "This is a test push notification")

    if not username or not user_service.exists(username):
        flash("User not found", "error")
        return redirect(url_for("admin.admin_dashboard"))

    result = push_manager.send_to_user(username, title, message)
    if result.get("sent", 0) > 0:
        flash(f"Sent to {username}! Sent: {result['sent']}, Failed: {result['failed']}", "success")
    else:
        flash(f"Failed: {result.get('error', 'Unknown')}", "error")
    return redirect(url_for("admin.admin_dashboard"))


@notifications_bp.route("/admin/send-all", methods=["POST"])
@admin_required
def admin_send_to_all():
    data = request.form or (request.get_json(silent=True) or {})
    title = data.get("title", "Important Update")
    message = data.get("message", "Check out the latest F1 news!")

    result = push_manager.send_to_all(title, message)
    total_users = len(push_manager.get_all_subscriptions())

    if result.get("sent", 0) > 0:
        flash(f"Sent to {total_users} users! Sent: {result['sent']}, Failed: {result['failed']}", "success")
    else:
        flash("No notifications sent", "warning")
    return redirect(url_for("admin.admin_dashboard"))


@notifications_bp.route("/admin/subscriptions/count", methods=["GET"])
@admin_required
def admin_subscription_count():
    all_subs = push_manager.get_all_subscriptions()
    return jsonify({
        "success": True,
        "total_subscriptions": push_manager.count_subscriptions(),
        "users_with_subscriptions": len(all_subs),
        "users_per_subscription": {k: len(v) for k, v in all_subs.items()},
    }), 200
