import datetime, json
from extensions import db

class User(db.Model):
    __tablename__ = "users"
    id                       = db.Column(db.Integer, primary_key=True)
    full_name                = db.Column(db.String(120), nullable=False)
    username                 = db.Column(db.String(40),  nullable=False, unique=True, index=True)
    email                    = db.Column(db.String(254),  nullable=False, unique=True, index=True)
    password_hash            = db.Column(db.String(255),  nullable=True)
    google_id                = db.Column(db.String(128),  nullable=True, unique=True)
    is_premium               = db.Column(db.Boolean, default=False, nullable=False)
    is_admin                 = db.Column(db.Boolean, default=False, nullable=False)
    email_verified           = db.Column(db.Boolean, default=False, nullable=False)
    email_verify_token       = db.Column(db.String(255), nullable=True)
    rewarded_scans           = db.Column(db.Integer, default=0, nullable=False)
    paystack_customer_code   = db.Column(db.String(100), nullable=True)
    paystack_subscription_code = db.Column(db.String(100), nullable=True)
    paystack_email_token     = db.Column(db.String(255), nullable=True)
    created_at               = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "id":             self.id,
            "full_name":      self.full_name,
            "username":       self.username,
            "email":          self.email,
            "is_premium":     self.is_premium,
            "is_admin":       self.is_admin,
            "email_verified": self.email_verified,
            "has_password":   bool(self.password_hash),
            "has_google":     bool(self.google_id),
            "rewarded_scans": self.rewarded_scans or 0,
            "created_at":     self.created_at.isoformat() if self.created_at else None,
        }


class ScanHistory(db.Model):
    __tablename__ = "scan_history"
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    scan_type  = db.Column(db.String(20), default="message", nullable=False)
    preview    = db.Column(db.String(200), nullable=False)
    verdict    = db.Column(db.String(20), nullable=False)
    score      = db.Column(db.Integer, nullable=False, default=0)
    flags      = db.Column(db.Text, nullable=True)
    scanned_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, index=True)
    user       = db.relationship("User", backref=db.backref("scans", lazy="dynamic", cascade="all, delete-orphan"))

    def to_dict(self):
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
    __tablename__ = "community_reports"
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    scam_type   = db.Column(db.String(40), nullable=False, default="other")
    description = db.Column(db.Text, nullable=False)
    verdict     = db.Column(db.String(20), nullable=True)
    score       = db.Column(db.Integer, nullable=True)
    reported_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, index=True)
    upvotes     = db.Column(db.Integer, default=0, nullable=False)

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