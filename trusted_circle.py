"""
trusted_circle.py

PREMIUM FEATURE — "Trusted Circle" (Veridict's version of Truecaller's
Family Protection, launched Dec 2025). One Premium account owner can
add family members by email. When any linked member scans something
that comes back suspicious or scam, the circle owner is notified and
can see a shared view of threats encountered across the family.

This directly targets what Truecaller's own research found: scammers
increasingly target entire households through multiple family members,
not just individuals.
"""

import datetime
from flask import Blueprint, request, jsonify, session
from extensions import db, limiter
from auth import login_required
from models import User, ScanHistory

trusted_circle_bp = Blueprint("trusted_circle", __name__, url_prefix="/api/trusted-circle")


# ──────────────────────────────────────────────────────────────
# MODEL — defined here to keep this feature self-contained.
# Import and register with db in models.py / app.py (see setup notes
# at the bottom of this file).
# ──────────────────────────────────────────────────────────────
class TrustedCircleMember(db.Model):
    __tablename__ = "trusted_circle_members"
    id            = db.Column(db.Integer, primary_key=True)
    owner_id      = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    member_email  = db.Column(db.String(254), nullable=False)
    member_id     = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status        = db.Column(db.String(20), default="pending", nullable=False)  # pending | active
    added_at      = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        member_user = User.query.get(self.member_id) if self.member_id else None
        return {
            "id":           self.id,
            "email":        self.member_email,
            "status":       self.status,
            "name":         member_user.full_name if member_user else None,
            "added_at":     self.added_at.isoformat() + "Z",
        }


MAX_CIRCLE_SIZE = 4  # owner + 4 members = 5 total, matching Truecaller's model


def _require_premium(user):
    if not user.is_premium:
        return jsonify({
            "message": "Trusted Circle is a Premium feature. Upgrade to protect your family too.",
            "upgrade_required": True
        }), 402
    return None


@trusted_circle_bp.route("", methods=["GET"])
@login_required
def get_circle():
    user = User.query.get(session["user_id"])
    if not user:
        return jsonify({"message": "Session expired."}), 401

    denial = _require_premium(user)
    if denial:
        return denial

    members = TrustedCircleMember.query.filter_by(owner_id=user.id).order_by(TrustedCircleMember.added_at.desc()).all()
    return jsonify({
        "members": [m.to_dict() for m in members],
        "max_size": MAX_CIRCLE_SIZE,
        "slots_remaining": max(0, MAX_CIRCLE_SIZE - len(members)),
    }), 200


@trusted_circle_bp.route("/add", methods=["POST"])
@login_required
@limiter.limit("10 per hour")
def add_member():
    user = User.query.get(session["user_id"])
    if not user:
        return jsonify({"message": "Session expired."}), 401

    denial = _require_premium(user)
    if denial:
        return denial

    data  = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()

    if not email or "@" not in email:
        return jsonify({"message": "Enter a valid email address."}), 400
    if email == user.email:
        return jsonify({"message": "You can't add yourself to your own circle."}), 400

    existing_count = TrustedCircleMember.query.filter_by(owner_id=user.id).count()
    if existing_count >= MAX_CIRCLE_SIZE:
        return jsonify({"message": f"Your Trusted Circle is full (max {MAX_CIRCLE_SIZE} members)."}), 400

    already = TrustedCircleMember.query.filter_by(owner_id=user.id, member_email=email).first()
    if already:
        return jsonify({"message": "This person is already in your Trusted Circle."}), 409

    linked_user = User.query.filter_by(email=email).first()
    member = TrustedCircleMember(
        owner_id=user.id,
        member_email=email,
        member_id=linked_user.id if linked_user else None,
        status="active" if linked_user else "pending",
    )
    db.session.add(member)
    db.session.commit()

    msg = "Added to your Trusted Circle." if linked_user else \
          "Invited — they'll be linked automatically once they create a Veridict account with this email."

    return jsonify({"message": msg, "member": member.to_dict()}), 201


@trusted_circle_bp.route("/<int:member_id>", methods=["DELETE"])
@login_required
def remove_member(member_id):
    user = User.query.get(session["user_id"])
    if not user:
        return jsonify({"message": "Session expired."}), 401

    member = TrustedCircleMember.query.filter_by(id=member_id, owner_id=user.id).first()
    if not member:
        return jsonify({"message": "Member not found."}), 404

    db.session.delete(member)
    db.session.commit()
    return jsonify({"message": "Removed from your Trusted Circle."}), 200


@trusted_circle_bp.route("/activity", methods=["GET"])
@login_required
def circle_activity():
    """Shared view: recent risky scans from every linked family member."""
    user = User.query.get(session["user_id"])
    if not user:
        return jsonify({"message": "Session expired."}), 401

    denial = _require_premium(user)
    if denial:
        return denial

    members = TrustedCircleMember.query.filter_by(owner_id=user.id, status="active").all()
    member_ids = [m.member_id for m in members if m.member_id]

    if not member_ids:
        return jsonify({"activity": []}), 200

    limit = min(int(request.args.get("limit", 30)), 100)
    rows = (ScanHistory.query
            .filter(ScanHistory.user_id.in_(member_ids))
            .filter(ScanHistory.verdict.in_(["scam", "suspicious"]))
            .order_by(ScanHistory.scanned_at.desc())
            .limit(limit)
            .all())

    activity = []
    for r in rows:
        scan_user = User.query.get(r.user_id)
        activity.append({
            "member_name": scan_user.full_name if scan_user else "Unknown",
            "member_email": scan_user.email if scan_user else "",
            "preview": r.preview,
            "verdict": r.verdict,
            "score": r.score,
            "scanned_at": r.scanned_at.isoformat() + "Z",
        })

    return jsonify({"activity": activity}), 200