"""Dedicated security and code-quality dashboards."""
from flask import Blueprint, render_template, request

from app.models import Finding, Review

bp = Blueprint("analysis", __name__)

SEVERITIES = ["Critical", "High", "Medium", "Low", "Informational"]


def _selected_review():
    review_id = request.args.get("review_id", type=int)
    if review_id:
        return Review.query.get(review_id)
    return None


@bp.get("/security")
def security_dashboard():
    review = _selected_review()
    query = Finding.query.filter(Finding.category == "Security")
    if review:
        query = query.filter(Finding.review_id == review.id)
    findings = query.all()
    severities = {name: sum(1 for f in findings if f.severity == name) for name in SEVERITIES}
    groups = {}
    for finding in findings:
        group = finding.category_group or "Other"
        groups[group] = groups.get(group, 0) + 1
    top_rules = {}
    for finding in findings:
        key = finding.rule_id or finding.title
        top_rules[key] = top_rules.get(key, 0) + 1
    reviews = Review.query.order_by(Review.created_at.desc()).all()
    return render_template("security.html", findings=findings, severities=severities,
                           groups=groups, top_rules=top_rules, reviews=reviews, selected=review,
                           risk_counts={name: sum(1 for r in reviews if r.risk_level == name) for name in ["Critical", "High", "Medium", "Low"]})


@bp.get("/quality")
def quality_dashboard():
    review = _selected_review()
    if review:
        reviews = [review]
    else:
        reviews = Review.query.order_by(Review.created_at.desc()).all()
    findings = Finding.query.filter(Finding.category.in_(["Quality", "Performance"]))
    if review:
        findings = findings.filter(Finding.review_id == review.id)
    quality_findings = findings.all()
    metrics = [item.metrics for item in reviews]
    avg = lambda key: round(sum(item.get(key, 0) for item in metrics) / len(metrics), 1) if metrics else 0
    trend = [{"date": item.created_at.strftime("%Y-%m-%d"), "score": item.quality_score,
              "complexity": item.metrics.get("max_complexity", 0)} for item in reversed(reviews[:14])]
    averages = {
        "quality": round(sum(item.quality_score for item in reviews) / len(reviews), 1) if reviews else 0,
        "complexity": avg("max_complexity"),
        "loc": avg("lines_of_code"),
        "functions": avg("function_count"),
        "classes": avg("class_count"),
        "maintainability": avg("maintainability_index"),
    }
    return render_template("quality.html", reviews=reviews, findings=quality_findings,
                           averages=averages, trend=trend, selected=review)
