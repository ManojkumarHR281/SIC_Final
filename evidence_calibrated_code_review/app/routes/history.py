"""Review history with search, filters, pagination and deletion."""
from flask import Blueprint, flash, redirect, render_template, request, url_for

from app import db
from app.models import Review

bp = Blueprint("history", __name__)
PER_PAGE = 10


def filtered_reviews(args):
    query = Review.query
    search = (args.get("q") or "").strip().lower()
    language = args.get("language") or ""
    severity = args.get("severity") or ""
    date_from = args.get("from") or ""
    date_to = args.get("to") or ""
    if search:
        query = query.filter(db.or_(Review.title.ilike(f"%{search}%"), Review.language.ilike(f"%{search}%")))
    if language:
        query = query.filter(Review.language == language)
    if severity:
        query = query.filter(Review.risk_level == severity)
    if date_from:
        query = query.filter(Review.created_at >= date_from)
    if date_to:
        query = query.filter(Review.created_at <= date_to + " 23:59:59")
    sort = args.get("sort", "newest")
    query = query.order_by({
        "oldest": Review.created_at.asc(),
        "findings": Review.total_findings.desc(),
    }.get(sort, Review.created_at.desc()))
    return query


@bp.get("/history")
def history():
    query = filtered_reviews(request.args)
    page = max(1, request.args.get("page", 1, type=int) or 1)
    pagination = query.paginate(page=page, per_page=PER_PAGE, error_out=False)
    languages = [row[0] for row in db.session.query(Review.language).distinct().all()]
    base_params = {key: value for key, value in request.args.items() if key != "page"}
    return render_template("history.html", reviews=pagination.items, pagination=pagination,
                           languages=languages, args=request.args, base_params=base_params)


@bp.post("/reviews/<int:review_id>/delete")
def delete_review(review_id):
    review = db.get_or_404(Review, review_id)
    db.session.delete(review)
    db.session.commit()
    flash("Review deleted.", "success")
    return redirect(url_for("history.history"))
