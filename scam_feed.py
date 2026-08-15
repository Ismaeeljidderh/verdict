"""
scam_feed.py

Public Scam Alert Feed — no login required. Shows recent scam patterns
pulled from Community Reports, so the page is genuinely useful to
anyone who lands on it (via search or a shared link), not just
existing users. Designed to drive organic search traffic and sharing.

Only shows reports that scored "suspicious" or "scam" via the scam
engine — filters out anything submitted that didn't actually look
risky, so the public feed stays trustworthy.
"""

from flask import Blueprint, jsonify, request
from models import CommunityReport

scam_feed_bp = Blueprint("scam_feed", __name__, url_prefix="/api/scam-feed")


@scam_feed_bp.route("", methods=["GET"])
def get_public_feed():
    """
    Public, unauthenticated endpoint. Returns recent risky community
    reports, paginated, optionally filtered by scam_type.
    """
    page  = max(1, int(request.args.get("page", 1)))
    limit = min(int(request.args.get("limit", 15)), 30)
    scam_type = (request.args.get("type") or "").strip().lower()

    query = CommunityReport.query.filter(CommunityReport.verdict.in_(["scam", "suspicious"]))

    if scam_type and scam_type != "all":
        query = query.filter(CommunityReport.scam_type == scam_type)

    total = query.count()
    rows = (query.order_by(CommunityReport.reported_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
            .all())

    return jsonify({
        "reports": [r.to_dict() for r in rows],
        "total": total,
        "page": page,
        "has_more": (page * limit) < total,
    }), 200


@scam_feed_bp.route("/stats", methods=["GET"])
def get_feed_stats():
    """Public counts — used to show 'X scams reported this week' type copy."""
    from datetime import datetime, timedelta
    week_ago = datetime.utcnow() - timedelta(days=7)

    total_reports = CommunityReport.query.filter(
        CommunityReport.verdict.in_(["scam", "suspicious"])
    ).count()

    this_week = CommunityReport.query.filter(
        CommunityReport.verdict.in_(["scam", "suspicious"]),
        CommunityReport.reported_at >= week_ago
    ).count()

    # Breakdown by type, for a "most common scams" summary
    from sqlalchemy import func
    from extensions import db
    type_counts = (db.session.query(CommunityReport.scam_type, func.count(CommunityReport.id))
                   .filter(CommunityReport.verdict.in_(["scam", "suspicious"]))
                   .group_by(CommunityReport.scam_type)
                   .order_by(func.count(CommunityReport.id).desc())
                   .limit(5)
                   .all())

    return jsonify({
        "total_reports": total_reports,
        "this_week": this_week,
        "top_types": [{"type": t, "count": c} for t, c in type_counts],
    }), 200