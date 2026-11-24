"""Report hub, analytics workspace and review comparison."""
from flask import Blueprint, jsonify, render_template, request

from app.models import Finding, Review
from app.routes.dashboard import stats_data
from app.services.comparison import compare_reviews

bp = Blueprint("reports", __name__)


@bp.get("/reports")
def reports():
    reviews = Review.query.order_by(Review.created_at.desc()).all()
    formats = [
        {"id": "pdf", "label": "PDF report", "icon": "bi-file-earmark-pdf", "description": "Formatted executive report with evidence and scores."},
        {"id": "json", "label": "JSON data", "icon": "bi-file-earmark-code", "description": "Complete structured data for integrations."},
        {"id": "csv", "label": "CSV findings", "icon": "bi-file-earmark-spreadsheet", "description": "Flat findings table for spreadsheets."},
        {"id": "markdown", "label": "Markdown", "icon": "bi-file-earmark-text", "description": "Portable text report for documentation."},
    ]
    return render_template("reports.html", reviews=reviews, formats=formats)


@bp.get("/analytics")
def analytics():
    days = request.args.get("range", "30")
    stats = stats_data(days)
    rules = {}
    for finding in Finding.query.all():
        key = finding.rule_id or finding.title
        rules[key] = rules.get(key, 0) + 1
    top_rules = sorted(rules.items(), key=lambda item: item[1], reverse=True)[:10]
    return render_template("analytics.html", stats=stats, top_rules=top_rules, active_range=str(days))


@bp.get("/compare")
def compare_page():
    reviews = Review.query.order_by(Review.created_at.desc()).all()
    left = request.args.get("left", type=int)
    right = request.args.get("right", type=int)
    result = compare_reviews(left, right) if left and right else None
    return render_template("compare.html", reviews=reviews, result=result, left=left, right=right)


@bp.get("/api/reviews/compare")
def compare_api():
    result = compare_reviews(request.args.get("left", type=int), request.args.get("right", type=int))
    if result is None:
        return jsonify({"error": "Both review IDs must exist."}), 404
    return jsonify(result)
