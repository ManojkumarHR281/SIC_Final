"""Review workflow, persistence, results and all export endpoints."""
import csv
import hashlib
import io
import json
import time

from flask import Blueprint, Response, flash, jsonify, redirect, render_template, request, url_for

from app import db, csrf
from app.models import Evidence, Finding, Review
from app.services.ai_provider import request_explanation
from app.services.fix_engine import apply_line_replacement, validate_fix
from app.services.report_generator import (finding_dict, generate_pdf, markdown_report,
                                           review_dict, review_json)
from app.services.review_engine import review_code
from app.utils.code_parser import json_dumps, line_with_pointer, snippet_at
from app.utils.settings_store import get_settings
from app.utils.validators import (MAX_CODE_BYTES, MAX_FILES, MAX_TOTAL_BYTES, validate_review,
                                  validate_upload, language_for_filename, safe_filename)

bp = Blueprint("review", __name__)
api_bp = Blueprint("review_api", __name__)
csrf.exempt(api_bp)

SAMPLES = {
    "Clean Python": 'def add(left, right):\n    """Return the sum of two numbers."""\n    return left + right\n',
    "Security risks": 'import os\nimport pickle\n\ndef load(raw):\n    password = "admin123"\n    query = "SELECT * FROM users WHERE name = " + raw\n    os.system("echo " + raw)\n    return pickle.loads(raw)\n',
    "Syntax error": 'def broken(:\n    pass\n',
}


def _finding_row(item, file_name, code):
    return Finding(
        title=item["title"], description=item["description"],
        category=item.get("category", "Quality"), severity=item["severity"],
        file_name=file_name, line_start=item.get("line"), line_end=item.get("line"),
        snippet=(item.get("snippet") or (snippet_at(code, item["line"]) or line_with_pointer(code, item["line"])) if item.get("line") else item.get("snippet", "")),
        confidence=item["confidence"], uncertainty=item["uncertainty"],
        confidence_level=item["confidence_level"], recommendation=item["recommendation"],
        suggested_fix=item.get("suggested_fix", ""), source=item["source"],
        rationale=item.get("rationale", ""),
        rule_id=item.get("rule_id", ""), column_no=item.get("column", 1),
        cwe=item.get("cwe", ""), category_group=item.get("category_group", ""),
        explanation=item.get("explanation") or item.get("description", ""),
        potential_impact=item.get("potential_impact", ""),
        fix_code=item.get("fix_code", ""), fix_valid=bool(item.get("fix_valid", False)),
        score_factors_json=json_dumps(item.get("score_factors", {})),
        model_probability=item.get("model_probability"),
        calibrated_probability=item.get("calibrated_probability"),
        model_version=item.get("model_version", ""),
    )


def persist_review(payload, files=None):
    """Analyze one or more uploaded/pasted files and persist a single review."""
    if files is None:
        files = [{"name": payload.get("file_name") or "submitted_code.py", "code": payload.get("code", "")}]
    if not files:
        return None, "Please provide source code or upload at least one file."
    if len(files) > MAX_FILES:
        return None, f"A review can contain at most {MAX_FILES} files."

    mode = payload.get("mode", "comprehensive")
    sensitivity = payload.get("sensitivity", "balanced")
    language = payload.get("language") or language_for_filename(files[0]["name"])
    if not isinstance(language, str) or language not in {"python", "javascript", "typescript", "java", "cpp", "c", "csharp", "php", "go", "ruby"}:
        return None, "Unsupported programming language."

    total_bytes = 0
    for item in files:
        if not isinstance(item, dict):
            return None, "Invalid file payload."
        item["name"] = safe_filename(item.get("name", "source.py"))
        item["code"] = item.get("code", "")
        error = validate_review(item["code"], language, mode, sensitivity)
        if error:
            return None, f"{item['name']}: {error}"
        size = len(item["code"].encode("utf-8"))
        total_bytes += size
        if size > MAX_CODE_BYTES or total_bytes > MAX_TOTAL_BYTES:
            return None, "The combined upload exceeds the 1.5 MB review limit."

    start = time.perf_counter()
    all_findings, combined_metrics, scores, ml_predictions = [], {}, [], []
    seen = set()
    preferences = get_settings()
    rule_scope = {"Security": "security", "Performance": "complexity", "Bug": "bugs",
                  "Syntax": "bugs", "Quality": "quality"}
    for item in files:
        analyzed = review_code(item["code"], language, mode, sensitivity, item["name"])
        combined_metrics = dict(analyzed.metrics)
        ml_predictions.append(analyzed.metrics.get("ml_prediction", {"available": False}))
        selected_findings = [
            finding for finding in analyzed
            if preferences["enabled_rules"].get(rule_scope.get(finding.get("category"), "quality"), True)
            and preferences["severity_preferences"].get(finding.get("severity"), True)
        ]
        for finding in selected_findings:
            key = (finding.get("rule_id") or finding["title"], item["name"], finding.get("line", 1), finding.get("column", 1))
            if key in seen:
                continue
            seen.add(key)
            all_findings.append((finding, item["name"], item["code"]))
        scores.append(analyzed.quality_score)

    digest_source = "\n".join(f"{item['name']}:{item['code']}" for item in files)
    review = Review(
        title=str(payload.get("title") or files[0]["name"] or "Code review")[:160],
        language=language, review_mode=mode,
        code_hash=hashlib.sha256(digest_source.encode("utf-8")).hexdigest(),
        code_size=total_bytes, duration=round(time.perf_counter() - start, 4),
        total_findings=len(all_findings),
        high_confidence_count=sum(f["confidence_level"] == "HIGH" for f, _, _ in all_findings),
        medium_confidence_count=sum(f["confidence_level"] == "MEDIUM" for f, _, _ in all_findings),
        low_confidence_count=sum(f["confidence_level"] == "LOW" for f, _, _ in all_findings),
        file_count=len(files),
        file_names_json=json_dumps([item["name"] for item in files]),
        source_files_json=json_dumps({item["name"]: item["code"] for item in files}) if str(payload.get("store_source", "")).lower() in {"1", "true", "on", "yes"} else "{}",
        quality_score=round(sum(scores) / len(scores), 1) if scores else 100.0,
        risk_level=_risk(all_findings),
        avg_confidence=round(sum(f["confidence"] for f, _, _ in all_findings) / len(all_findings), 4) if all_findings else 0,
        avg_uncertainty=round(sum(f["uncertainty"] for f, _, _ in all_findings) / len(all_findings), 4) if all_findings else 0,
        metrics_json=json_dumps({**combined_metrics, "ml_samples_analyzed": len(files),
                                 "ml_available_samples": sum(bool(p.get("available")) for p in ml_predictions),
                                 "ml_file_predictions": ml_predictions}),
    )
    db.session.add(review)
    for finding, file_name, code in all_findings:
        row = _finding_row(finding, file_name, code)
        review.findings.append(row)
        for evidence in finding.get("evidence", []):
            row.evidence.append(Evidence(
                source=evidence["source"], evidence_type=evidence["evidence_type"],
                description=evidence["description"], strength=evidence["strength"],
                verified=bool(evidence["verified"]),
                metadata_json=json_dumps({"rule_id": finding.get("rule_id", ""), "line": finding.get("line", 1)}),
            ))
    db.session.commit()
    return review, None


def _risk(findings):
    confirmed = [f for f, _, _ in findings if f["severity"] in {"High", "Critical"} and f["confidence"] >= .7]
    if any(f["severity"] == "Critical" and f["confidence"] >= .7 for f in confirmed):
        return "Critical"
    if len(confirmed) >= 2:
        return "High"
    if confirmed or sum(1 for f, _, _ in findings if f["severity"] == "Medium") >= 3:
        return "Medium"
    return "Low"


@bp.get("/review/new")
def new_review():
    return render_template("review.html", samples=SAMPLES)


@bp.post("/review/new")
def submit_review():
    uploaded = [item for item in request.files.getlist("files") if item and item.filename]
    if not uploaded:
        single = request.files.get("file")
        uploaded = [single] if single and single.filename else []
    files = []
    for item in uploaded:
        name = safe_filename(item.filename)
        error = validate_upload(name, item.content_length or MAX_CODE_BYTES)
        if error:
            flash(error, "danger")
            return redirect(url_for("review.new_review"))
        code = item.stream.read(MAX_TOTAL_BYTES).decode("utf-8", errors="replace")
        if "\x00" in code:
            flash(f"{name}: uploaded file contains binary content.", "danger")
            return redirect(url_for("review.new_review"))
        files.append({"name": name, "code": code})
    pasted = request.form.get("code", "")
    if pasted.strip() and len(files) < MAX_FILES:
        files.append({"name": safe_filename(request.form.get("file_name") or "pasted_code.py"), "code": pasted})
    if not files:
        flash("Please paste source code or choose a supported file.", "danger")
        return redirect(url_for("review.new_review"))
    review, error = persist_review({**request.form, "language": request.form.get("language") or "python"}, files)
    if error:
        flash(error, "danger")
        return redirect(url_for("review.new_review"))
    flash(f"Analysis complete: {review.total_findings} finding(s) across {review.file_count} file(s).", "success")
    return redirect(url_for("review.results", review_id=review.id))


@bp.get("/reviews/<int:review_id>")
def results(review_id):
    review = db.get_or_404(Review, review_id)
    return render_template("review_results.html", review=review, findings=review.findings)


@bp.get("/api/reviews")
@api_bp.get("/api/reviews")
def api_reviews():
    rows = Review.query.order_by(Review.created_at.desc()).all()
    return jsonify([review_dict(item) for item in rows])


@api_bp.post("/api/review")
def api_review():
    payload = request.get_json(silent=True) or {}
    files = payload.get("files")
    if files is not None and not isinstance(files, list):
        return jsonify({"error": "files must be a list."}), 400
    review, error = persist_review(payload, files)
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"id": review.id, "total_findings": review.total_findings,
                    "quality_score": review.quality_score, "risk_level": review.risk_level,
                    "metrics": review.metrics,
                    "findings": [finding_dict(f) for f in review.findings]}), 201


@bp.get("/reviews/<int:review_id>/export/json")
@api_bp.get("/api/reviews/<int:review_id>")
def export_json(review_id):
    review = db.get_or_404(Review, review_id)
    return Response(review_json(review), mimetype="application/json",
                    headers={"Content-Disposition": f"attachment; filename=review-{review_id}.json"})


@api_bp.delete("/api/reviews/<int:review_id>")
def delete_review_api(review_id):
    review = db.get_or_404(Review, review_id)
    db.session.delete(review)
    db.session.commit()
    return "", 204


@bp.get("/reviews/<int:review_id>/export/csv")
def export_csv(review_id):
    review = db.get_or_404(Review, review_id)
    output = io.StringIO()
    fields = ["rule_id", "title", "severity", "category", "cwe", "file_name", "line_start",
              "column_no", "model_probability", "calibrated_probability", "model_version",
              "confidence", "uncertainty", "description", "recommendation", "source"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for finding in review.findings:
        writer.writerow({
            "rule_id": finding.rule_id, "title": finding.title, "severity": finding.severity,
            "category": finding.category, "cwe": finding.cwe, "file_name": finding.file_name,
            "line_start": finding.line_start, "column_no": finding.column_no,
            "confidence": finding.confidence, "uncertainty": finding.uncertainty,
            "model_probability": finding.model_probability,
            "calibrated_probability": finding.calibrated_probability,
            "model_version": finding.model_version,
            "description": finding.description, "recommendation": finding.recommendation,
            "source": finding.source,
        })
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=review-{review_id}.csv"})


@bp.get("/reviews/<int:review_id>/report")
def report(review_id):
    review = db.get_or_404(Review, review_id)
    return Response(markdown_report(review), mimetype="text/markdown",
                    headers={"Content-Disposition": f"attachment; filename=review-{review_id}.md"})


@bp.get("/reviews/<int:review_id>/export/pdf")
def export_pdf(review_id):
    review = db.get_or_404(Review, review_id)
    return Response(generate_pdf(review), mimetype="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=review-{review_id}.pdf"})


@bp.get("/samples/<string:name>")
def sample_source(name):
    from flask import abort
    if name not in SAMPLES:
        abort(404)
    return Response(SAMPLES[name], mimetype="text/plain")
