import json, re
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, session
from auth import login_required
from extensions import db, limiter
from models import User, ScanHistory, CommunityReport
from scam_engine import analyze_content

scan_bp = Blueprint("scan", __name__, url_prefix="/api")
FREE_WEEKLY_SCAN_LIMIT = 5


@scan_bp.route("/scan", methods=["POST"])
@login_required
@limiter.limit("30 per minute")
def scan_content():
    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    if not content: return jsonify({"message": "Paste a message, link, or text to scan."}), 400
    if len(content) > 5000: return jsonify({"message": "Too long — keep it under 5000 characters."}), 400
    scan_type = (data.get("type") or "message").strip().lower()
    if scan_type not in ("message","website","email","phone","screenshot"): scan_type = "message"

    user = User.query.get(session["user_id"])
    if not user: return jsonify({"message": "Session expired."}), 401
    if not user.is_premium:
        week_ago = datetime.utcnow() - timedelta(days=7)
        weekly = ScanHistory.query.filter_by(user_id=user.id).filter(ScanHistory.scanned_at >= week_ago).count()
        limit  = FREE_WEEKLY_SCAN_LIMIT + (user.rewarded_scans or 0)
        if weekly >= limit:
            return jsonify({"message": f"You've used all {limit} scans this week. Watch an ad for 3 more, or upgrade.","upgrade_required": True}), 402

    result = analyze_content(content)
    entry = ScanHistory(user_id=user.id, scan_type=scan_type,
        preview=content[:90] + ("…" if len(content) > 90 else ""),
        verdict=result["verdict"], score=result["score"], flags=json.dumps(result["flags"]))
    db.session.add(entry); db.session.commit()

    response = entry.to_dict()
    response["recommended_actions"] = result["recommended_actions"]
    if user.is_premium:
        response["explanation"] = result["explanation"]
    else:
        response["explanation"] = None
        response["explanation_locked"] = True
    return jsonify(response), 200


@scan_bp.route("/scan/history", methods=["GET"])
@login_required
def scan_history():
    limit = min(int(request.args.get("limit", 50)), 200)
    rows = (ScanHistory.query.filter_by(user_id=session["user_id"])
            .order_by(ScanHistory.scanned_at.desc()).limit(limit).all())
    return jsonify({"history": [r.to_dict() for r in rows]}), 200


@scan_bp.route("/scan/stats", methods=["GET"])
@login_required
def scan_stats():
    user_id = session["user_id"]
    user = User.query.get(user_id)
    is_premium = bool(user and user.is_premium)
    rewarded = int(user.rewarded_scans or 0) if user else 0
    total = ScanHistory.query.filter_by(user_id=user_id).count()
    threats = ScanHistory.query.filter_by(user_id=user_id).filter(ScanHistory.verdict.in_(["scam","suspicious"])).count()
    safe = total - threats
    week_ago = datetime.utcnow() - timedelta(days=7)
    weekly_used = ScanHistory.query.filter_by(user_id=user_id).filter(ScanHistory.scanned_at >= week_ago).count()
    remaining = None if is_premium else max(0, FREE_WEEKLY_SCAN_LIMIT + rewarded - weekly_used)
    return jsonify({"total_scans": total, "threats_blocked": threats, "safe_scans": safe,
        "free_scans_remaining": remaining, "rewarded_scans": rewarded, "is_premium": is_premium}), 200


@scan_bp.route("/scan/export", methods=["GET"])
@login_required
def export_history():
    import csv, io
    from flask import Response
    rows = (ScanHistory.query.filter_by(user_id=session["user_id"]).order_by(ScanHistory.scanned_at.desc()).all())
    output = io.StringIO(); writer = csv.writer(output)
    writer.writerow(["ID","Type","Preview","Verdict","Score","Flags","Scanned At"])
    for r in rows:
        writer.writerow([r.id, r.scan_type, r.preview, r.verdict, r.score,
            "; ".join(json.loads(r.flags) if r.flags else []), r.scanned_at.strftime("%Y-%m-%d %H:%M:%S UTC")])
    return Response(output.getvalue(), mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=veridict-scan-history.csv"})


@scan_bp.route("/scan/reward-ad", methods=["POST"])
@login_required
@limiter.limit("5 per hour")
def reward_ad():
    data = request.get_json(silent=True) or {}
    token = (data.get("ad_token") or "").strip()
    user = User.query.get(session["user_id"])
    if not user: return jsonify({"message": "Session expired."}), 401
    if user.is_premium: return jsonify({"message": "You're on Premium already!"}), 400
    if not token: return jsonify({"message": "Ad token missing."}), 400
    BONUS = 3
    user.rewarded_scans = (user.rewarded_scans or 0) + BONUS
    db.session.commit()
    return jsonify({"message": f"You earned {BONUS} bonus scans!", "bonus_granted": BONUS, "rewarded_scans": user.rewarded_scans}), 200


@scan_bp.route("/scan/demo", methods=["POST"])
@limiter.limit("6 per hour")
def demo_scan():
    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    if not content: return jsonify({"message": "Paste something to scan."}), 400
    if len(content) > 1000: return jsonify({"message": "Demo limited to 1000 characters."}), 400
    result = analyze_content(content)
    return jsonify({"verdict": result["verdict"], "score": result["score"],
        "flags": result["flags"][:3], "explanation": result["explanation"], "demo": True}), 200


@scan_bp.route("/scan/qr", methods=["POST"])
@login_required
@limiter.limit("20 per minute")
def scan_qr():
    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    if not content: return jsonify({"message": "No QR content provided."}), 400
    user = User.query.get(session["user_id"])
    if not user: return jsonify({"message": "Session expired."}), 401
    if not user.is_premium:
        week_ago = datetime.utcnow() - timedelta(days=7)
        weekly = ScanHistory.query.filter_by(user_id=user.id).filter(ScanHistory.scanned_at >= week_ago).count()
        limit = FREE_WEEKLY_SCAN_LIMIT + (user.rewarded_scans or 0)
        if weekly >= limit:
            return jsonify({"message": "Weekly scan limit reached.","upgrade_required": True}), 402

    text_result = analyze_content(content)
    url_result = None
    if re.search(r"https?://|www\.", content, re.IGNORECASE):
        from tools import _analyze_url
        url_result = _analyze_url(content)

    if url_result:
        combined_score = max(text_result["score"], url_result["score"])
        combined_flags = list(dict.fromkeys(text_result["flags"] + url_result["flags"]))[:8]
    else:
        combined_score = text_result["score"]; combined_flags = text_result["flags"]

    verdict = "scam" if combined_score >= 55 else ("suspicious" if combined_score >= 25 else "safe")
    entry = ScanHistory(user_id=user.id, scan_type="qr",
        preview=content[:90] + ("…" if len(content) > 90 else ""),
        verdict=verdict, score=combined_score, flags=json.dumps(combined_flags))
    db.session.add(entry); db.session.commit()

    response = entry.to_dict()
    response["explanation"] = text_result["explanation"]
    if url_result: response["url_details"] = url_result["details"]
    return jsonify(response), 200


@scan_bp.route("/scan/community/reports", methods=["GET"])
def get_community_reports():
    page = max(1, int(request.args.get("page", 1)))
    limit = min(int(request.args.get("limit", 20)), 50)
    rows = (CommunityReport.query.order_by(CommunityReport.reported_at.desc())
            .offset((page-1)*limit).limit(limit).all())
    total = CommunityReport.query.count()
    return jsonify({"reports": [r.to_dict() for r in rows], "total": total}), 200


@scan_bp.route("/scan/community/reports", methods=["POST"])
@login_required
@limiter.limit("5 per hour")
def submit_community_report():
    data = request.get_json(silent=True) or {}
    scam_type = (data.get("scam_type") or "other").strip()[:40]
    description = (data.get("description") or "").strip()
    if not description or len(description) < 20:
        return jsonify({"message": "Description must be at least 20 characters."}), 400
    if len(description) > 2000: return jsonify({"message": "Too long — max 2000 characters."}), 400
    result = analyze_content(description)
    report = CommunityReport(user_id=session["user_id"], scam_type=scam_type,
        description=description, verdict=result["verdict"], score=result["score"])
    db.session.add(report); db.session.commit()
    return jsonify({"message": "Report submitted. Thank you!", "report": report.to_dict()}), 201


@scan_bp.route("/scan/community/reports/<int:rid>/upvote", methods=["POST"])
@login_required
@limiter.limit("20 per minute")
def upvote_report(rid):
    report = CommunityReport.query.get(rid)
    if not report: return jsonify({"message": "Report not found."}), 404
    report.upvotes = (report.upvotes or 0) + 1
    db.session.commit()
    return jsonify({"upvotes": report.upvotes}), 200


@scan_bp.route("/scan/bulk", methods=["POST"])
@login_required
@limiter.limit("10 per hour")
def bulk_scan():
    """PREMIUM-ONLY: Scan up to 20 messages/links at once."""
    user = User.query.get(session["user_id"])
    if not user: return jsonify({"message": "Session expired."}), 401
    if not user.is_premium:
        return jsonify({"message": "Bulk scanning is a Premium feature. Upgrade to scan multiple items at once.",
            "upgrade_required": True}), 402

    data = request.get_json(silent=True) or {}
    items = data.get("items") or []
    scan_type = (data.get("type") or "message").strip().lower()
    if scan_type not in ("message","website","email","phone"): scan_type = "message"
    if not isinstance(items, list) or not items:
        return jsonify({"message": "Provide a list of items to scan."}), 400
    items = [str(i).strip() for i in items if str(i).strip()][:20]
    if not items: return jsonify({"message": "No valid items to scan."}), 400

    results = []
    for content in items:
        if len(content) > 5000: content = content[:5000]
        result = analyze_content(content)
        entry = ScanHistory(user_id=user.id, scan_type=scan_type,
            preview=content[:90] + ("…" if len(content) > 90 else ""),
            verdict=result["verdict"], score=result["score"], flags=json.dumps(result["flags"]))
        db.session.add(entry)
        results.append({"preview": content[:90], "verdict": result["verdict"],
            "score": result["score"], "flags": result["flags"], "explanation": result["explanation"]})

    db.session.commit()
    threats_found = sum(1 for r in results if r["verdict"] != "safe")
    return jsonify({"results": results, "total_scanned": len(results), "threats_found": threats_found}), 200

@scan_bp.route("/scan/export-pdf", methods=["GET"])
@login_required
def export_history_pdf():
    """PREMIUM-ONLY: Export scan history as a formatted PDF report,
    suitable for sharing with a bank, police report, or personal records."""
    user = User.query.get(session["user_id"])
    if not user:
        return jsonify({"message": "Session expired."}), 401
    if not user.is_premium:
        return jsonify({"message": "PDF export is a Premium feature. Upgrade to download formatted reports.",
            "upgrade_required": True}), 402

    from io import BytesIO
    from flask import Response
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    rows = (ScanHistory.query.filter_by(user_id=user.id)
            .order_by(ScanHistory.scanned_at.desc()).all())

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.6*inch, bottomMargin=0.6*inch)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("VTitle", parent=styles["Heading1"], fontSize=18, spaceAfter=4)
    sub_style   = ParagraphStyle("VSub", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#666666"), spaceAfter=18)

    elements = [
        Paragraph("Veridict — Scan History Report", title_style),
        Paragraph(f"Generated for: {user.full_name or user.username} ({user.email})", sub_style),
        Paragraph(f"Total scans: {len(rows)} &nbsp;&nbsp;|&nbsp;&nbsp; Threats flagged: {sum(1 for r in rows if r.verdict != 'safe')}", sub_style),
        Spacer(1, 6),
    ]

    table_data = [["Date", "Type", "Verdict", "Score", "Preview"]]
    for r in rows:
        table_data.append([
            r.scanned_at.strftime("%Y-%m-%d %H:%M"),
            r.scan_type.title(),
            r.verdict.title(),
            f"{r.score}/100",
            (r.preview[:60] + "…") if len(r.preview) > 60 else r.preview,
        ])

    table = Table(table_data, colWidths=[1.1*inch, 0.8*inch, 0.9*inch, 0.6*inch, 2.6*inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#15161a")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#dddddd")),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f7f7f7")]),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("Generated by Veridict — AI-powered scam detection. This report reflects automated analysis and should be used alongside your own judgment.", sub_style))

    doc.build(elements)
    buffer.seek(0)

    return Response(buffer.read(), mimetype="application/pdf",
        headers={"Content-Disposition": "attachment; filename=veridict-scan-report.pdf"})