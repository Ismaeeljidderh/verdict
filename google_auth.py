"""
google_auth.py
Google OAuth login flow using Authlib.

  GET /api/auth/google/login     -> redirects to Google's consent screen
  GET /api/auth/google/callback  -> Google redirects back here; we verify
                                     the token, find-or-create the user,
                                     log them in, and redirect to the dashboard.

Requires GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET to be set as env vars
(see .env.example). Without them, the login route fails gracefully with
a redirect back to the login page and an error flag the frontend can
show a message for.
"""

import re
import secrets
from urllib.parse import urlencode

from flask import Blueprint, redirect, url_for, session, request

from extensions import db, oauth
from models import User

google_auth_bp = Blueprint("google_auth", __name__, url_prefix="/api/auth/google")


@google_auth_bp.route("/login")
def google_login():
    if not oauth.google:
        return redirect("/login?google_error=not_configured")

    redirect_uri = url_for("google_auth.google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@google_auth_bp.route("/callback")
def google_callback():
    if not oauth.google:
        return redirect("/login?google_error=not_configured")

    try:
        token = oauth.google.authorize_access_token()
        userinfo = token.get("userinfo")
        if not userinfo:
            userinfo = oauth.google.userinfo()
    except Exception:
        return redirect("/login?google_error=auth_failed")

    google_id = userinfo.get("sub")
    email = (userinfo.get("email") or "").strip().lower()
    full_name = userinfo.get("name") or email.split("@")[0]

    if not google_id or not email:
        return redirect("/login?google_error=auth_failed")

    # Find by google_id first, then fall back to email (links an
    # existing password account to Google on first OAuth login).
    user = User.query.filter_by(google_id=google_id).first()
    if not user:
        user = User.query.filter_by(email=email).first()

    if user:
        if not user.google_id:
            user.google_id = google_id
            db.session.commit()
    else:
        username = _generate_unique_username(email)
        user = User(
            full_name=full_name,
            username=username,
            email=email,
            google_id=google_id,
        )
        db.session.add(user)
        db.session.commit()

    session.clear()
    session["user_id"] = user.id

    return redirect("/dashboard")


def _generate_unique_username(email):
    """Derive a username from the email's local part, appending digits
    if needed to avoid colliding with an existing username."""
    base = re.sub(r"[^a-zA-Z0-9_]", "", email.split("@")[0])[:16] or "user"
    candidate = base
    suffix = 0
    while User.query.filter_by(username=candidate).first():
        suffix += 1
        candidate = f"{base}{suffix}"
    return candidate
