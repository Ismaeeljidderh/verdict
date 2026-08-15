"""
billing.py
Paystack-powered Premium subscription ($10/month). Stripe doesn't
support Nigerian merchants, so this uses Paystack instead — it's
built for the Nigerian market and supports card, bank transfer,
and USSD payment methods.

  POST /api/billing/create-checkout-session  -> { url }  (redirect user here)
  GET  /api/billing/callback                 -> Paystack redirects here after payment
  POST /api/billing/webhook                  -> Paystack calls this server-to-server
  POST /api/billing/cancel-subscription      -> disables the recurring subscription

Requires PAYSTACK_SECRET_KEY and PAYSTACK_PLAN_CODE env vars (see
.env.example). Routes fail gracefully with a clear message if
Paystack isn't configured yet, rather than crashing.

Docs: https://paystack.com/docs/payments/subscriptions/
"""

import os
import hmac
import hashlib

import requests
from flask import Blueprint, request, jsonify, session, current_app, redirect

from auth import login_required
from extensions import db
from models import User

billing_bp = Blueprint("billing", __name__, url_prefix="/api/billing")

PAYSTACK_BASE_URL = "https://api.paystack.co"


def _paystack_configured():
    return bool(os.environ.get("PAYSTACK_SECRET_KEY") and os.environ.get("PAYSTACK_PLAN_CODE"))


def _paystack_headers():
    return {
        "Authorization": f"Bearer {os.environ.get('PAYSTACK_SECRET_KEY', '')}",
        "Content-Type": "application/json",
    }


@billing_bp.route("/create-checkout-session", methods=["POST"])
@login_required
def create_checkout_session():
    if not _paystack_configured():
        return jsonify({"message": "Payments aren't configured on this server yet."}), 503

    user = User.query.get(session["user_id"])
    if not user:
        return jsonify({"message": "Session expired."}), 401

    if user.is_premium:
        return jsonify({"message": "You're already on Premium."}), 400

    site_url = os.environ.get("SITE_URL", request.url_root.rstrip("/"))

    try:
        resp = requests.post(
            f"{PAYSTACK_BASE_URL}/transaction/initialize",
            headers=_paystack_headers(),
            json={
                "email": user.email,
                "plan": os.environ["PAYSTACK_PLAN_CODE"],
                "callback_url": f"{site_url}/api/billing/callback",
                "metadata": {"user_id": user.id},
            },
            timeout=10,
        )
        data = resp.json()
    except Exception as exc:
        current_app.logger.error("Paystack init error: %s", exc)
        return jsonify({"message": "Could not start checkout. Please try again."}), 502

    if not data.get("status"):
        current_app.logger.error("Paystack init failed: %s", data)
        return jsonify({"message": data.get("message", "Could not start checkout.")}), 502

    return jsonify({"url": data["data"]["authorization_url"]}), 200


@billing_bp.route("/callback", methods=["GET"])
def paystack_callback():
    """
    Paystack redirects the user's browser here after payment. We verify
    the transaction server-side before trusting it (the webhook also
    does this independently as the source of truth, in case the user
    closes the tab before this redirect completes).
    """
    if not _paystack_configured():
        return redirect("/dashboard?upgrade=cancelled")

    reference = request.args.get("reference") or request.args.get("trxref")
    if not reference:
        return redirect("/dashboard?upgrade=cancelled")

    try:
        resp = requests.get(
            f"{PAYSTACK_BASE_URL}/transaction/verify/{reference}",
            headers=_paystack_headers(),
            timeout=10,
        )
        data = resp.json()
    except Exception as exc:
        current_app.logger.error("Paystack verify error: %s", exc)
        return redirect("/dashboard?upgrade=cancelled")

    if data.get("status") and data["data"]["status"] == "success":
        _activate_premium_from_transaction(data["data"])
        return redirect("/dashboard?upgrade=success")

    return redirect("/dashboard?upgrade=cancelled")


def _activate_premium_from_transaction(tx_data):
    metadata = tx_data.get("metadata") or {}
    user_id = metadata.get("user_id")
    customer = tx_data.get("customer") or {}

    user = None
    if user_id:
        user = User.query.get(user_id)
    if not user and customer.get("email"):
        user = User.query.filter_by(email=customer["email"].lower()).first()

    if not user:
        return

    user.is_premium = True
    if customer.get("customer_code"):
        user.paystack_customer_code = customer["customer_code"]

    plan_obj = tx_data.get("plan_object") or {}
    subscription_code = tx_data.get("subscription_code") or plan_obj.get("subscription_code")
    if subscription_code:
        user.paystack_subscription_code = subscription_code

    db.session.commit()


@billing_bp.route("/webhook", methods=["POST"])
def paystack_webhook():
    """
    Paystack calls this directly (no browser session, no CSRF token),
    so this route is CSRF-exempt — see app.py. Authenticity is instead
    verified via Paystack's HMAC SHA512 signature header.
    """
    if not _paystack_configured():
        return jsonify({"message": "Paystack not configured."}), 503

    secret = os.environ.get("PAYSTACK_SECRET_KEY", "").encode("utf-8")
    signature = request.headers.get("x-paystack-signature", "")
    computed = hmac.new(secret, request.data, hashlib.sha512).hexdigest()

    if not hmac.compare_digest(computed, signature):
        return jsonify({"message": "Invalid webhook signature."}), 400

    event = request.get_json(silent=True) or {}
    event_type = event.get("event")
    payload = event.get("data") or {}

    if event_type == "charge.success":
        _activate_premium_from_transaction(payload)

    elif event_type == "subscription.create":
        customer = payload.get("customer") or {}
        email = (customer.get("email") or "").lower()
        user = User.query.filter_by(email=email).first()
        if user:
            user.is_premium = True
            user.paystack_subscription_code = payload.get("subscription_code")
            user.paystack_email_token = payload.get("email_token")
            if customer.get("customer_code"):
                user.paystack_customer_code = customer["customer_code"]
            db.session.commit()

    elif event_type in ("subscription.disable", "subscription.not_renew"):
        subscription_code = payload.get("subscription_code")
        user = User.query.filter_by(paystack_subscription_code=subscription_code).first()
        if user:
            user.is_premium = False
            db.session.commit()

    elif event_type == "invoice.payment_failed":
        customer = payload.get("customer") or {}
        email = (customer.get("email") or "").lower()
        user = User.query.filter_by(email=email).first()
        if user:
            user.is_premium = False
            db.session.commit()

    return jsonify({"received": True}), 200


@billing_bp.route("/cancel-subscription", methods=["POST"])
@login_required
def cancel_subscription():
    if not _paystack_configured():
        return jsonify({"message": "Payments aren't configured on this server yet."}), 503

    user = User.query.get(session["user_id"])
    if not user or not user.paystack_subscription_code or not user.paystack_email_token:
        return jsonify({"message": "No active subscription found to cancel."}), 400

    try:
        resp = requests.post(
            f"{PAYSTACK_BASE_URL}/subscription/disable",
            headers=_paystack_headers(),
            json={
                "code": user.paystack_subscription_code,
                "token": user.paystack_email_token,
            },
            timeout=10,
        )
        data = resp.json()
    except Exception as exc:
        current_app.logger.error("Paystack cancel error: %s", exc)
        return jsonify({"message": "Could not cancel subscription. Please try again."}), 502

    if not data.get("status"):
        return jsonify({"message": data.get("message", "Could not cancel subscription.")}), 502

    user.is_premium = False
    db.session.commit()

    return jsonify({"message": "Subscription cancelled. You're back on the Free plan."}), 200
