"""
models.py
Database models for Veridict. Currently just the User model;
will grow as scan history / subscription tiers are added.
"""

from datetime import datetime
from extensions import db, bcrypt


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(60), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=True)  # nullable: Google-only accounts have no password
    google_id = db.Column(db.String(255), unique=True, nullable=True, index=True)
    is_premium = db.Column(db.Boolean, default=False, nullable=False)
    paystack_customer_code = db.Column(db.String(255), unique=True, nullable=True, index=True)
    paystack_subscription_code = db.Column(db.String(255), unique=True, nullable=True)
    paystack_email_token = db.Column(db.String(255), nullable=True)
    rewarded_scans       = db.Column(db.Integer, default=0, nullable=False)
    email_verified       = db.Column(db.Boolean, default=False, nullable=False)
    email_verify_token   = db.Column(db.String(255), nullable=True)
    is_admin             = db.Column(db.Boolean, default=False, nullable=False)
    email_verified       = db.Column(db.Boolean, default=False, nullable=False)
    bonus_scans = db.Column(db.Integer, default=0, nullable=False)  # earned via rewarded ads
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, raw_password):
        self.password_hash = bcrypt.generate_password_hash(raw_password).decode("utf-8")

    def check_password(self, raw_password):
        if not self.password_hash:
            return False  # Google-only account; no password set
        return bcrypt.check_password_hash(self.password_hash, raw_password)

    def to_public_dict(self):
        """Safe subset of fields for sending to the client (never the hash)."""
        return {
            "id": self.id,
            "full_name": self.full_name,
            "username": self.username,
            "email": self.email,
            "is_premium": self.is_premium,
            "has_password": bool(self.password_hash),
            "has_google": bool(self.google_id),
            "email_verified": bool(self.email_verified),
            "is_admin": bool(self.is_admin),
            "email_verified": self.email_verified,
            "rewarded_scans": self.rewarded_scans or 0,
            "bonus_scans": self.bonus_scans or 0,
        }

class ScanHistory(db.Model):
    """Persistent scan history — replaces the in-memory _SCAN_HISTORY dict."""
    __tablename__ = "scan_history"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    scan_type  = db.Column(db.String(20),  default="message", nullable=False)
    preview    = db.Column(db.String(200), nullable=False)
    verdict    = db.Column(db.String(20),  nullable=False)   # safe | suspicious | scam
    score      = db.Column(db.Integer,     nullable=False, default=0)
    flags      = db.Column(db.Text,        nullable=True)    # JSON array stored as text
    scanned_at = db.Column(db.DateTime,    default=__import__("datetime").datetime.utcnow)

    user = db.relationship("User", backref=db.backref("scans", lazy="dynamic", cascade="all, delete-orphan"))

    def to_dict(self):
        import json
        return {
            "id":         self.id,
            "type":       self.scan_type,
            "preview":    self.preview,
            "verdict":    self.verdict,
            "score":      self.score,
            "flags":      json.loads(self.flags) if self.flags else [],
            "scanned_at": self.scanned_at.isoformat() + "Z",
        }


class CommunityReport(db.Model):
    """Crowd-sourced scam reports from the community."""
    __tablename__ = "community_reports"

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    scam_type   = db.Column(db.String(40),  nullable=False, default="other")
    description = db.Column(db.Text,        nullable=False)
    verdict     = db.Column(db.String(20),  nullable=True)   # from auto-scan
    score       = db.Column(db.Integer,     nullable=True)
    reported_at = db.Column(db.DateTime,    default=__import__("datetime").datetime.utcnow, index=True)
    upvotes     = db.Column(db.Integer,     default=0, nullable=False)

    def to_dict(self):
        return {
            "id":          self.id,
            "scam_type":   self.scam_type,
            "description": self.description[:300],
            "verdict":     self.verdict,
            "score":       self.score,
            "reported_at": self.reported_at.isoformat() + "Z",
            "upvotes":     self.upvotes,
        }
