import os, hashlib, hmac, requests
from flask import Blueprint, request, jsonify, session, redirect
from extensions import db, oauth, limiter
from models import User

billing_bp = Blueprint("billing", __name__, url_prefix="/api/billing")
google_auth_bp = Blueprint("google_auth", __name__, url_prefix="/api/auth/google")

PAYSTACK_BASE = "https://api.paystack.co"


def _paystack_key():
    return os.environ.get("PAYSTACK_SECRET_KEY", "")


@billing_bp.route("/create-checkout-session", methods=["POST"])
def create_checkout():
    if not session.get("user_id"):
        return jsonify({"message": "Please log in first."}), 401
    key = _paystack_key()
    if not key:
        return jsonify({"message": "Payments aren't configured yet. Contact support."}), 503

    user = User.query.get(session["user_id"])
    plan_code = os.environ.get("PAYSTACK_PLAN_CODE", "")
    try:
        r = requests.post(f"{PAYSTACK_BASE}/transaction/initialize",
            headers={"Authorization": f"Bearer {key}"},
            json={"email": user.email, "plan": plan_code,
                  "callback_url": request.host_url.rstrip("/") + "/api/billing/callback"})
        data = r.json()
        if data.get("status"):
            return jsonify({"url": data["data"]["authorization_url"]}), 200
        return jsonify({"message": data.get("message", "Could not start checkout.")}), 400
    except Exception:
        return jsonify({"message": "Payment service unavailable. Try again later."}), 503


@billing_bp.route("/callback")
def billing_callback():
    ref = request.args.get("reference", "")
    key = _paystack_key()
    if not key or not ref:
        return redirect("/plan?status=error")
    try:
        r = requests.get(f"{PAYSTACK_BASE}/transaction/verify/{ref}",
            headers={"Authorization": f"Bearer {key}"})
        data = r.json()
        if data.get("status") and data["data"]["status"] == "success":
            email = data["data"]["customer"]["email"]
            user = User.query.filter_by(email=email).first()
            if user:
                user.is_premium = True
                user.paystack_customer_code = data["data"]["customer"].get("customer_code")
                db.session.commit()
            return redirect("/plan?status=success")
    except Exception:
        pass
    return redirect("/plan?status=error")


@billing_bp.route("/webhook", methods=["POST"])
def billing_webhook():
    key = _paystack_key()
    signature = request.headers.get("x-paystack-signature", "")
    if key:
        computed = hmac.new(key.encode(), request.data, hashlib.sha512).hexdigest()
        if not hmac.compare_digest(computed, signature):
            return jsonify({"message": "Invalid signature"}), 401

    event = request.get_json(silent=True) or {}
    event_type = event.get("event", "")
    data = event.get("data", {})

    if event_type == "charge.success":
        email = data.get("customer", {}).get("email")
        user = User.query.filter_by(email=email).first()
        if user:
            user.is_premium = True
            db.session.commit()
    elif event_type == "subscription.disable":
        code = data.get("subscription_code")
        user = User.query.filter_by(paystack_subscription_code=code).first()
        if user:
            user.is_premium = False
            db.session.commit()

    return jsonify({"status": "ok"}), 200


@billing_bp.route("/cancel-subscription", methods=["POST"])
def cancel_subscription():
    if not session.get("user_id"):
        return jsonify({"message": "Please log in first."}), 401
    user = User.query.get(session["user_id"])
    key = _paystack_key()
    if not key:
        user.is_premium = False
        db.session.commit()
        return jsonify({"message": "Subscription cancelled."}), 200
    try:
        if user.paystack_subscription_code:
            requests.post(f"{PAYSTACK_BASE}/subscription/disable",
                headers={"Authorization": f"Bearer {key}"},
                json={"code": user.paystack_subscription_code, "token": user.paystack_email_token})
        user.is_premium = False
        db.session.commit()
        return jsonify({"message": "Subscription cancelled successfully."}), 200
    except Exception:
        return jsonify({"message": "Could not cancel. Contact support."}), 500


# ── Google OAuth ──
def init_google_oauth(app):
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    if client_id and client_secret:
        oauth.register(
            name="google",
            client_id=client_id,
            client_secret=client_secret,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )


@google_auth_bp.route("/login")
@limiter.limit("20 per hour")
def google_login():
    if not os.environ.get("GOOGLE_CLIENT_ID"):
        return redirect("/login?google_error=not_configured")
    redirect_uri = request.host_url.rstrip("/") + "/api/auth/google/callback"
    return oauth.google.authorize_redirect(redirect_uri)


@google_auth_bp.route("/callback")
def google_callback():
    try:
        token = oauth.google.authorize_access_token()
        userinfo = token.get("userinfo") or oauth.google.parse_id_token(token)
        google_id = userinfo["sub"]
        email     = userinfo["email"]
        name      = userinfo.get("name", email.split("@")[0])

        user = User.query.filter_by(google_id=google_id).first()
        if not user:
            user = User.query.filter_by(email=email).first()
            if user:
                user.google_id = google_id
            else:
                username = email.split("@")[0][:20]
                base_username = username
                i = 1
                while User.query.filter_by(username=username).first():
                    username = f"{base_username}{i}"; i += 1
                user = User(full_name=name, username=username, email=email,
                            google_id=google_id, email_verified=True)
                db.session.add(user)
            db.session.commit()

        session.clear(); session["user_id"] = user.id
        return redirect("/dashboard")
    except Exception:
        return redirect("/login?google_error=auth_failed")