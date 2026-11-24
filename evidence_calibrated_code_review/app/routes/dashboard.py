"""Database-backed analytics for the dashboard and charts."""
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, render_template, request

from app.models import Finding, Review

bp = Blueprint("dashboard", __name__)

SEVERITIES = ["Critical", "High", "Medium", "Low", "Informational"]
CONFIDENCE_LEVELS = ["HIGH", "MEDIUM", "LOW"]


def _period(days):
    if not days or days == "all":
        return None
    return datetime.now(timezone.utc) - timedelta(days=int(days))


def _in_range(query, start):
    return query.filter(Review.created_at >= start) if start else query


def stats_data(days=30):
    start = _period(days)
    reviews = _in_range(Review.query, start).order_by(Review.created_at.desc()).all()
    review_ids = [item.id for item in reviews]
    findings = Finding.query.filter(Finding.review_id.in_(review_ids)).all() if review_ids else []

    previous_start = None
    if start:
        span = datetime.now(timezone.utc) - start
        previous_start = start - span
    previous_reviews = Review.query.filter(Review.created_at >= previous_start, Review.created_at < start).all() if previous_start else []
    previous_ids = [item.id for item in previous_reviews]
    previous_findings = Finding.query.filter(Finding.review_id.in_(previous_ids)).all() if previous_ids else []

    def trend(current, earlier):
        if not earlier:
            return {"value": current, "delta": None, "direction": "new" if current else "flat"}
        change = (current - earlier) / earlier * 100
        return {"value": current, "delta": round(change, 1),
                "direction": "up" if change > 0 else "down" if change < 0 else "flat"}

    severity = {key: sum(1 for f in findings if f.severity == key) for key in SEVERITIES}
    confidence = {key: sum(1 for f in findings if f.confidence_level == key) for key in CONFIDENCE_LEVELS}
    categories = {key: sum(1 for f in findings if f.category == key) for key in ["Security", "Bug", "Syntax", "Performance", "Quality"]}
    security_groups = {}
    for finding in findings:
        if finding.category == "Security":
            group = finding.category_group or "Other"
            security_groups[group] = security_groups.get(group, 0) + 1

    by_day = {}
    for review in reviews:
        key = review.created_at.strftime("%Y-%m-%d")
        row = by_day.setdefault(key, {"reviews": 0, "findings": 0, "quality": 0.0})
        row["reviews"] += 1
        row["findings"] += review.total_findings
        row["quality"] += review.quality_score or 0
    timeline = [{"date": key, **{k: (round(v / by_day[key]["reviews"], 1) if k == "quality" else v) for k, v in row.items()}}
                for key, row in sorted(by_day.items())]

    trends = {
        "total_reviews": trend(len(reviews), len(previous_reviews)),
        "total_issues": trend(len(findings), len(previous_findings)),
        "critical": trend(severity["Critical"], sum(1 for f in previous_findings if f.severity == "Critical")),
        "high_severity": trend(severity["High"], sum(1 for f in previous_findings if f.severity == "High")),
    }
    return {
        "range": days,
        "total_reviews": len(reviews),
        "total_issues": len(findings),
        "critical": severity["Critical"],
        "high_severity": severity["High"],
        "trends": trends,
        "avg_confidence": round(sum(f.confidence for f in findings) / len(findings), 4) if findings else 0,
        "avg_uncertainty": round(sum(f.uncertainty for f in findings) / len(findings), 4) if findings else 0,
        "files_analyzed": sum(item.file_count for item in reviews),
        "successful_reviews": sum(1 for item in reviews if item.status == "complete"),
        "severity": severity,
        "confidence": confidence,
        "categories": categories,
        "security_groups": security_groups or {},
        "quality_score": round(sum(item.quality_score for item in reviews) / len(reviews), 1) if reviews else 0,
        "risk_level": "Critical" if severity["Critical"] else "High" if severity["High"] else "Medium" if severity["Medium"] else "Low",
        "timeline": timeline,
        "recent": [{
            "id": item.id, "title": item.title, "file_name": item.file_names[0] if item.file_names else "submitted_code.py",
            "language": item.language, "date": item.created_at.isoformat(), "findings": item.total_findings,
            "risk": item.risk_level, "status": item.status, "quality": item.quality_score,
        } for item in reviews[:8]],
    }


@bp.get("/")
def dashboard():
    days = request.args.get("range", "30")
    return render_template("dashboard.html", stats=stats_data(days), recent=Review.query.order_by(Review.created_at.desc()).limit(8).all(), active_range=str(days))


@bp.get("/api/dashboard/stats")
def stats_api():
    return jsonify(stats_data(request.args.get("range", "30")))
