"""Serialize persisted reviews for JSON, CSV, Markdown and PDF export."""
import io
import json

def finding_dict(f):
    data = {
        "id": f.id, "rule_id": getattr(f, "rule_id", ""), "title": f.title,
        "description": f.description, "explanation": getattr(f, "explanation", "") or f.description,
        "category": f.category, "category_group": getattr(f, "category_group", ""),
        "severity": f.severity, "cwe": getattr(f, "cwe", ""),
        "file_name": f.file_name, "line_start": f.line_start, "line_end": f.line_end,
        "column": getattr(f, "column_no", 1), "snippet": f.snippet,
        "confidence": f.confidence, "uncertainty": f.uncertainty,
        "model_probability": getattr(f, "model_probability", None),
        "calibrated_probability": getattr(f, "calibrated_probability", None),
        "model_version": getattr(f, "model_version", ""),
        "confidence_level": f.confidence_level, "recommendation": f.recommendation,
        "suggested_fix": f.suggested_fix, "source": f.source, "status": f.status,
        "rationale": f.rationale, "score_factors": getattr(f, "score_factors", {}),
        "evidence": [{"source": e.source, "type": e.evidence_type, "description": e.description,
                      "strength": e.strength, "verified": e.verified} for e in f.evidence],
    }
    return data


def review_dict(review):
    return {
        "id": review.id, "title": review.title, "language": review.language,
        "mode": review.review_mode, "created_at": review.created_at.isoformat(),
        "status": review.status, "total_findings": review.total_findings,
        "quality_score": getattr(review, "quality_score", 0),
        "risk_level": getattr(review, "risk_level", "Low"),
        "metrics": review.metrics, "file_names": review.file_names,
        "findings": [finding_dict(item) for item in review.findings],
    }


def markdown_report(review):
    lines = [
        f"# {review.title}", "",
        f"- Review ID: {review.id}",
        f"- Date: {review.created_at.isoformat()}",
        f"- Language: {review.language}",
        f"- Mode: {review.review_mode}",
        f"- Files: {', '.join(review.file_names) or 'submitted_code.py'}",
        f"- Findings: {review.total_findings}",
        f"- Quality score: {getattr(review, 'quality_score', 0):.1f}/100",
        f"- Security risk: {getattr(review, 'risk_level', 'Low')}", "",
        "## Executive summary", "",
        f"The analysis produced {review.total_findings} finding(s). Scores are heuristic evidence-based estimates, not empirically calibrated probabilities.", "",
        "## Findings", "",
    ]
    for f in review.findings:
        lines.extend([
            f"### {f.severity}: {f.title}", "",
            f"- Rule: {getattr(f, 'rule_id', '')}",
            f"- Location: {f.file_name}:{f.line_start}:{getattr(f, 'column_no', 1)}",
            f"- Category: {f.category} / {getattr(f, 'category_group', '')}",
            f"- confidence {f.confidence:.0%} ({f.confidence_level})",
            f"- Uncertainty: {f.uncertainty:.0%}",
            f"- CWE: {getattr(f, 'cwe', '') or 'n/a'}", "",
            f.description, "",
            f"**Recommendation:** {f.recommendation}", "",
        ])
        if f.snippet:
            lines.extend(["```", f.snippet, "```", ""])
        if f.rationale:
            lines.extend([f"*Scoring rationale:* {f.rationale}", ""])
    return "\n".join(lines)


def _footer(canvas, document):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.drawString(18 * mm, 12 * mm, "Evidence-Calibrated Code Review · Local analysis report")
    canvas.drawRightString(A4[0] - 18 * mm, 12 * mm, f"Page {document.page}")
    canvas.restoreState()


def generate_pdf(review):
    """Build a professional PDF report from persisted data."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=20 * mm,
        title=f"Review {review.id} - {review.title}", author="Evidence-Calibrated Code Review",
    )
    styles = getSampleStyleSheet()
    heading = ParagraphStyle("HeadingDark", parent=styles["Heading1"], textColor=colors.HexColor("#0B1120"), fontSize=20)
    sub = ParagraphStyle("Sub", parent=styles["Normal"], textColor=colors.HexColor("#475569"), fontSize=10)
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontSize=9, leading=13)
    title_style = ParagraphStyle("TitleDark", parent=styles["Heading2"], textColor=colors.HexColor("#1E293B"), fontSize=13)
    center = ParagraphStyle("Center", parent=sub, alignment=TA_CENTER)

    story = [
        Paragraph("CODE REVIEW REPORT", center), Spacer(1, 4 * mm),
        Paragraph(review.title, heading), Spacer(1, 2 * mm),
        Paragraph(f"Review #{review.id} · {review.created_at.strftime('%Y-%m-%d %H:%M UTC')}", sub),
        Spacer(1, 6 * mm),
    ]
    summary_rows = [
        ["Metric", "Value"],
        ["Language", review.language],
        ["Analysis mode", review.review_mode],
        ["Files", str(len(review.file_names) or 1)],
        ["Total findings", str(review.total_findings)],
        ["Quality score", f"{getattr(review, 'quality_score', 0):.1f}/100"],
        ["Security risk", getattr(review, "risk_level", "Low")],
        ["Average confidence", f"{getattr(review, 'avg_confidence', 0):.0%}"],
        ["Average uncertainty", f"{getattr(review, 'avg_uncertainty', 0):.0%}"],
    ]
    table = Table(summary_rows, colWidths=[55 * mm, 105 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), .5, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.extend([table, Spacer(1, 6 * mm), Paragraph("Executive summary", title_style), Spacer(1, 2 * mm)])
    metrics = review.metrics
    story.append(Paragraph(
        f"Static analysis examined {metrics.get('lines_of_code', 0)} lines of code across "
        f"{metrics.get('function_count', 0)} function(s) and {metrics.get('class_count', 0)} class(es). "
        f"Maximum cyclomatic complexity was {metrics.get('max_complexity', 0)}. "
        f"Confidence values are evidence-based estimates and are not empirically calibrated probabilities.",
        body,
    ))
    story.extend([Spacer(1, 5 * mm), Paragraph("Detailed findings", title_style), Spacer(1, 2 * mm)])

    if not review.findings:
        story.append(Paragraph("No findings were produced for this review.", body))
    for index, f in enumerate(review.findings, start=1):
        story.extend([
            Paragraph(f"{index}. {f.severity} · {f.title}", title_style),
            Paragraph(f"Rule {getattr(f, 'rule_id', '') or 'n/a'} · {f.file_name}:{f.line_start}:{getattr(f, 'column_no', 1)} · CWE {getattr(f, 'cwe', '') or 'n/a'}", sub),
            Spacer(1, 2 * mm),
            Paragraph(f.description.replace("<", "&lt;"), body),
            Paragraph(f"<b>Impact:</b> {(getattr(f, 'potential_impact', '') or 'See description.').replace('<', '&lt;')}", body),
            Paragraph(f"<b>Confidence:</b> {f.confidence:.0%} ({f.confidence_level}) · <b>Uncertainty:</b> {f.uncertainty:.0%}", body),
            Paragraph(f"<b>Recommendation:</b> {f.recommendation.replace('<', '&lt;')}", body),
        ])
        if f.evidence:
            story.append(Paragraph("<b>Evidence</b>", body))
            for evidence in f.evidence:
                story.append(Paragraph(f"• {evidence.description.replace('<', '&lt;')} (strength {evidence.strength:.0%}, verified: {bool(evidence.verified)})", body))
        story.append(Spacer(1, 4 * mm))
        if index % 4 == 0:
            story.append(PageBreak())

    story.extend([Spacer(1, 4 * mm), Paragraph("Final assessment", title_style)])
    story.append(Paragraph(
        f"Overall quality score: {getattr(review, 'quality_score', 0):.1f}/100. Security risk level: "
        f"{getattr(review, 'risk_level', 'Low')}. Findings reflect deterministic static observations and "
        f"clearly labelled heuristics; runtime behavior was not executed or verified.", body,
    ))
    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()


def review_json(review):
    return json.dumps(review_dict(review), indent=2)
