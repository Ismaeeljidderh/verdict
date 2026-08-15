import re
from functools import wraps
from flask import Blueprint, request, jsonify, session
from extensions import db, bcrypt, limiter
from models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/api")


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"message": "Authentication required."}), 401
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"message": "Authentication required."}), 401
        user = User.query.get(session["user_id"])
        if not user or not user.is_admin:
            return jsonify({"message": "Admin access required."}), 403
        return f(*args, **kwargs)
    return decorated


# ── CSRF token ──
@auth_bp.route("/csrf-token")
def csrf_token():
    from flask_wtf.csrf import generate_csrf
    return jsonify({"csrf_token": generate_csrf()})


# ── Health ──
@auth_bp.route("/health")
def health():
    return jsonify({"status": "ok"})


# ── Register ──
@auth_bp.route("/register", methods=["POST"])
@limiter.limit("10 per hour")
def register():
    data      = request.get_json(silent=True) or {}
    full_name = (data.get("full_name") or "").strip()
    username  = (data.get("username")  or "").strip().lower()
    email     = (data.get("email")     or "").strip().lower()
    password  = (data.get("password")  or "")

    if not full_name or not username or not email or not password:
        return jsonify({"message": "All fields are required."}), 400
    if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
        return jsonify({"message": "Username must be 3-20 characters: letters, numbers, underscores."}), 400
    if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
        return jsonify({"message": "Enter a valid email address."}), 400
    if len(password) < 8:
        return jsonify({"message": "Password must be at least 8 characters."}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"message": "An account with this email already exists."}), 409
    if User.query.filter_by(username=username).first():
        return jsonify({"message": "This username is already taken."}), 409

    pw_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    user    = User(full_name=full_name, username=username, email=email, password_hash=pw_hash)
    db.session.add(user); db.session.commit()

    try:
        from mailer import generate_reset_token, send_verification_email
        from flask import request as req
        token = generate_reset_token(email + ":verify")
        user.email_verify_token = token; db.session.commit()
        verify_url = req.host_url.rstrip("/") + f"/verify-email?token={token}"
        send_verification_email(email, verify_url, full_name)
    except Exception:
        pass

    session.clear(); session["user_id"] = user.id
    return jsonify({"message": "Account created!", "redirect": "/dashboard"}), 201


# ── Login ──
@auth_bp.route("/login", methods=["POST"])
@limiter.limit("20 per hour")
def login():
    data     = request.get_json(silent=True) or {}
    email    = (data.get("email")    or "").strip().lower()
    password = (data.get("password") or "")
    remember = bool(data.get("remember", False))

    user = User.query.filter_by(email=email).first()
    if not user or not user.password_hash or not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({"message": "Invalid email or password."}), 401

    session.clear(); session["user_id"] = user.id
    if remember: session.permanent = True
    return jsonify({"message": "Welcome back!", "redirect": "/dashboard"}), 200


# ── Logout ──
@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out.", "redirect": "/"}), 200


# ── Get/Update/Delete me ──
@auth_bp.route("/me", methods=["GET", "PUT", "DELETE"])
@login_required
def me():
    user = User.query.get(session["user_id"])
    if not user: return jsonify({"message": "User not found."}), 404

    if request.method == "GET":
        return jsonify(user.to_dict()), 200

    if request.method == "PUT":
        data      = request.get_json(silent=True) or {}
        full_name = (data.get("full_name") or "").strip()
        username  = (data.get("username")  or "").strip().lower()
        if not full_name: return jsonify({"message": "Full name is required."}), 400
        if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
            return jsonify({"message": "Invalid username format."}), 400
        existing = User.query.filter_by(username=username).first()
        if existing and existing.id != user.id:
            return jsonify({"message": "Username already taken."}), 409
        user.full_name = full_name; user.username = username
        db.session.commit()
        return jsonify({"message": "Profile updated.", **user.to_dict()}), 200

    if request.method == "DELETE":
        data = request.get_json(silent=True) or {}
        if data.get("confirm") != "DELETE":
            return jsonify({"message": "Type DELETE to confirm."}), 400
        db.session.delete(user); db.session.commit()
        session.clear()
        return jsonify({"message": "Account deleted.", "redirect": "/"}), 200


# ── Change password ──
@auth_bp.route("/change-password", methods=["POST"])
@login_required
def change_password():
    user = User.query.get(session["user_id"])
    data = request.get_json(silent=True) or {}
    cur  = data.get("current_password", "")
    new  = data.get("new_password", "")
    if not user.password_hash or not bcrypt.check_password_hash(user.password_hash, cur):
        return jsonify({"message": "Current password is incorrect."}), 401
    if len(new) < 8:
        return jsonify({"message": "New password must be at least 8 characters."}), 400
    user.password_hash = bcrypt.generate_password_hash(new).decode("utf-8")
    db.session.commit()
    return jsonify({"message": "Password updated successfully."}), 200


# ── Forgot password ──
@auth_bp.route("/forgot-password", methods=["POST"])
@limiter.limit("5 per hour")
def forgot_password():
    data  = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    user  = User.query.filter_by(email=email).first()
    # Always return success to prevent email enumeration
    if user and user.password_hash:
        try:
            from mailer import generate_reset_token, send_password_reset_email
            token = generate_reset_token(email)
            reset_url = request.host_url.rstrip("/") + f"/reset-password?token={token}"
            send_password_reset_email(email, reset_url, user.full_name)
        except Exception:
            pass
    return jsonify({"message": "If that email exists, a reset link has been sent. Check your inbox (and spam)."}), 200


# ── Reset password ──
@auth_bp.route("/reset-password", methods=["POST"])
@limiter.limit("10 per hour")
def reset_password():
    from mailer import verify_reset_token
    data     = request.get_json(silent=True) or {}
    token    = (data.get("token") or "").strip()
    new_pass = data.get("new_password", "")
    if not token: return jsonify({"message": "Missing token."}), 400
    email = verify_reset_token(token, max_age_seconds=3600)
    if not email: return jsonify({"message": "This link has expired or is invalid. Request a new one."}), 400
    user = User.query.filter_by(email=email).first()
    if not user: return jsonify({"message": "Account not found."}), 404
    if len(new_pass) < 8: return jsonify({"message": "Password must be at least 8 characters."}), 400
    user.password_hash = bcrypt.generate_password_hash(new_pass).decode("utf-8")
    db.session.commit()
    session.clear(); session["user_id"] = user.id
    return jsonify({"message": "Password reset successfully.", "redirect": "/dashboard"}), 200


# ── Email verify ──
@auth_bp.route("/verify-email", methods=["POST"])
@limiter.limit("10 per hour")
def verify_email():
    from mailer import verify_reset_token
    data  = request.get_json(silent=True) or {}
    token = (data.get("token") or "").strip()
    if not token: return jsonify({"message": "Missing token."}), 400
    raw = verify_reset_token(token, max_age_seconds=86400)
    if not raw or not raw.endswith(":verify"):
        return jsonify({"message": "Link expired or invalid. Request a new one from your dashboard."}), 400
    email = raw[:-7]
    user  = User.query.filter_by(email=email).first()
    if not user: return jsonify({"message": "Account not found."}), 404
    user.email_verified = True; user.email_verify_token = None
    db.session.commit()
    session.clear(); session["user_id"] = user.id
    return jsonify({"message": "Email verified! Welcome to Veridict.", "redirect": "/dashboard"}), 200


# ── Resend verify ──
@auth_bp.route("/resend-verification", methods=["POST"])
@login_required
@limiter.limit("3 per hour")
def resend_verification():
    user = User.query.get(session["user_id"])
    if not user: return jsonify({"message": "Session expired."}), 401
    if user.email_verified: return jsonify({"message": "Email already verified."}), 400
    from mailer import generate_reset_token, send_verification_email
    token = generate_reset_token(user.email + ":verify")
    user.email_verify_token = token; db.session.commit()
    verify_url = request.host_url.rstrip("/") + f"/verify-email?token={token}"
    send_verification_email(user.email, verify_url, user.full_name)
    return jsonify({"message": "Verification email sent! Check your inbox."}), 200


# ── Admin routes ──
@auth_bp.route("/admin/stats")
@admin_required
def admin_stats():
    from models import ScanHistory
    return jsonify({
        "total_users":   User.query.count(),
        "premium_users": User.query.filter_by(is_premium=True).count(),
        "total_scans":   ScanHistory.query.count(),
        "total_threats": ScanHistory.query.filter(ScanHistory.verdict.in_(["scam","suspicious"])).count(),
    }), 200


@auth_bp.route("/admin/users")
@admin_required
def admin_users():
    from models import ScanHistory
    users = User.query.order_by(User.created_at.desc()).all()
    result = []
    for u in users:
        result.append({**u.to_dict(), "scan_count": ScanHistory.query.filter_by(user_id=u.id).count()})
    return jsonify({"users": result}), 200


@auth_bp.route("/admin/users/<int:uid>/toggle-premium", methods=["POST"])
@admin_required
def admin_toggle_premium(uid):
    data = request.get_json(silent=True) or {}
    user = User.query.get(uid)
    if not user: return jsonify({"message": "User not found."}), 404
    user.is_premium = bool(data.get("is_premium", not user.is_premium))
    db.session.commit()
    return jsonify({"message": f"Premium {'granted' if user.is_premium else 'removed'}.", "is_premium": user.is_premium}), 200


@auth_bp.route("/admin/users/<int:uid>", methods=["DELETE"])
@admin_required
def admin_delete_user(uid):
    user = User.query.get(uid)
    if not user: return jsonify({"message": "User not found."}), 404
    if user.is_admin: return jsonify({"message": "Cannot delete another admin."}), 403
    db.session.delete(user); db.session.commit()
    return jsonify({"message": f"User {user.email} deleted."}), 200