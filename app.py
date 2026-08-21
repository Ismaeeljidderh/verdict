"""
app.py — Veridict application factory
"""
import os
from datetime import timedelta
from flask import Flask, send_from_directory, session, redirect, jsonify

# Load .env file automatically — works whether or not python-dotenv is installed
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Fine — env vars can still be set manually

from extensions import db, bcrypt, csrf, limiter, oauth
from auth import auth_bp, login_required
from business_check import business_bp
from url_analyzer import url_analyzer_bp
from google_auth import google_auth_bp
from scan import scan_bp
from billing import billing_bp
from trusted_circle import trusted_circle_bp
from scam_feed import scam_feed_bp


BASE_DIR    = os.path.abspath(os.path.dirname(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")


def create_app():
    app = Flask(__name__, static_folder=None)

    # ---------------------------------------------------------
    # CONFIG
    # ---------------------------------------------------------
    app.config["SECRET_KEY"]                = os.environ.get("SECRET_KEY", "dev-secret-veridict-2024")

    # Render's free Postgres gives connection strings starting with
    # "postgres://", but SQLAlchemy 1.4+ requires "postgresql://" —
    # this rewrites it automatically so the same DATABASE_URL just works.
    _db_url = os.environ.get("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'veridict.db')}")
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"]   = _db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Session cookies
    app.config["SESSION_COOKIE_HTTPONLY"]  = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"]   = os.environ.get("FLASK_ENV") == "production"
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=14)

    # CSRF — accept token from header on JSON/fetch requests
    app.config["WTF_CSRF_HEADERS"]       = ["X-CSRFToken", "X-CSRF-Token"]
    app.config["WTF_CSRF_TIME_LIMIT"]    = None   # never expire within a session
    app.config["WTF_CSRF_SSL_STRICT"]    = False  # allow http on localhost

    # Google OAuth
    app.config["GOOGLE_CLIENT_ID"]     = os.environ.get("GOOGLE_CLIENT_ID", "")
    app.config["GOOGLE_CLIENT_SECRET"] = os.environ.get("GOOGLE_CLIENT_SECRET", "")

    # Paystack
    app.config["SITE_URL"] = os.environ.get("SITE_URL", "http://localhost:5000")

    # Flask-Limiter: explicit in-memory store (avoids deprecation warnings)
    app.config["RATELIMIT_STORAGE_URI"] = "memory://"

    # ---------------------------------------------------------
    # EXTENSIONS
    # ---------------------------------------------------------
    db.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    oauth.init_app(app)

    if app.config["GOOGLE_CLIENT_ID"] and app.config["GOOGLE_CLIENT_SECRET"]:
        oauth.register(
            name="google",
            client_id=app.config["GOOGLE_CLIENT_ID"],
            client_secret=app.config["GOOGLE_CLIENT_SECRET"],
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )

    # ---------------------------------------------------------
    # BLUEPRINTS
    # ---------------------------------------------------------
    app.register_blueprint(auth_bp)
    app.register_blueprint(google_auth_bp)
    app.register_blueprint(scan_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(business_bp)
    app.register_blueprint(url_analyzer_bp)
    app.register_blueprint(trusted_circle_bp)
    app.register_blueprint(scam_feed_bp)

    csrf.exempt(google_auth_bp)
    from billing import paystack_webhook
    csrf.exempt(paystack_webhook)

    # ---------------------------------------------------------
    # FRONTEND ROUTES
    # ---------------------------------------------------------
    @app.route("/")
    def serve_landing():
        if session.get("user_id"):
            return redirect("/dashboard")
        return send_from_directory(FRONTEND_DIR, "landing.html")

    @app.route("/login")
    def serve_login():
        if session.get("user_id"):
            return redirect("/dashboard")
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.route("/scam-feed")
    def serve_scam_feed():
     return send_from_directory(FRONTEND_DIR, "scam-feed.html")

    @app.route("/trusted-circle")
    def serve_trusted_circle():
        if not session.get("user_id"):
            return redirect("/login")
        return send_from_directory(FRONTEND_DIR, "trusted-circle.html")

    @app.route("/register")
    def serve_register():
        if session.get("user_id"):
            return redirect("/dashboard")
        return send_from_directory(FRONTEND_DIR, "register.html")

    @app.route("/business-checker")
    def serve_business_checker():
        return send_from_directory(FRONTEND_DIR, "business-checker.html")

    @app.route("/url-analyzer")
    def serve_url_analyzer():
        return send_from_directory(FRONTEND_DIR, "url-analyzer.html")

    @app.route("/qr-scanner")
    def serve_qr_scanner():
        if not session.get("user_id"):
            return redirect("/login")
        return send_from_directory(FRONTEND_DIR, "qr-scanner.html")

    @app.route("/verify-email")
    def serve_verify_email():
        return send_from_directory(FRONTEND_DIR, "verify-email.html")

    @app.route("/reset-password")
    def serve_reset_password():
        return send_from_directory(FRONTEND_DIR, "reset-password.html")

    @app.route("/scanner")
    def serve_scanner():
        if not session.get("user_id"):
            return redirect("/login")
        return send_from_directory(FRONTEND_DIR, "scanner.html")

    @app.route("/dashboard")
    def serve_dashboard():
        if not session.get("user_id"):
            return redirect("/login")
        return send_from_directory(FRONTEND_DIR, "dashboard.html")

    @app.route("/<path:filename>")
    def serve_static(filename):
        return send_from_directory(FRONTEND_DIR, filename)

    # ---------------------------------------------------------
    # HEALTH CHECK — visit /api/health in browser to verify
    # ---------------------------------------------------------
    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok", "message": "Veridict is running."}), 200

    @app.route("/tips")
    def serve_tips():
        return send_from_directory(FRONTEND_DIR, "tips.html")

    @app.route("/alerts")
    def serve_alerts():
        if not session.get("user_id"):
            return redirect("/login")
        return send_from_directory(FRONTEND_DIR, "alerts.html")

    @app.route("/plan")
    def serve_plan():
        if not session.get("user_id"):
            return redirect("/login")
        return send_from_directory(FRONTEND_DIR, "plan.html")

    

    @app.route("/admin")
    def serve_admin():
        if not session.get("user_id"):
            return redirect("/login")
        from models import User
        user = User.query.get(session["user_id"])
        if not user or not user.is_admin:
            return redirect("/dashboard")
        return send_from_directory(FRONTEND_DIR, "admin.html")

    @app.route("/settings")
    def serve_settings():
        if not session.get("user_id"):
            return redirect("/login")
        return send_from_directory(FRONTEND_DIR, "settings.html")

    @app.route("/community")
    def serve_community():
        if not session.get("user_id"):
            return redirect("/login")
        return send_from_directory(FRONTEND_DIR, "community.html")

    @app.route("/about")
    def serve_about():
        return send_from_directory(FRONTEND_DIR, "about.html")

    @app.route("/terms")
    def serve_terms():
        return send_from_directory(FRONTEND_DIR, "terms.html")

    @app.route("/privacy")
    def serve_privacy():
        return send_from_directory(FRONTEND_DIR, "privacy.html")

    @app.route("/contact")
    def serve_contact():
        return send_from_directory(FRONTEND_DIR, "contact.html")

    # ---------------------------------------------------------
    # ERROR PAGES
    # ---------------------------------------------------------
    @app.errorhandler(404)
    def not_found(e):
        return send_from_directory(FRONTEND_DIR, "404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        app.logger.error("500 error: %s", e)
        return send_from_directory(FRONTEND_DIR, "500.html"), 500

    # ---------------------------------------------------------
    # DB SETUP
    # ---------------------------------------------------------
    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)