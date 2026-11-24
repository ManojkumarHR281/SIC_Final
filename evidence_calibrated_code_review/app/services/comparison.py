"""Deterministic comparison of two persisted reviews."""
from app import db
from app.models import Review


def _signature(finding):
    return (finding.rule_id or finding.title, finding.file_name, finding.title)


def _match_key(finding):
    return (_signature(finding), finding.line_start or 0)


def compare_reviews(left_id, right_id):
    if not left_id or not right_id:
        return None
    left = db.session.get(Review, left_id)
    right = db.session.get(Review, right_id)
    if left is None or right is None:
        return None

    left_rows, right_rows = list(left.findings), list(right.findings)
    left_by_sig = {}
    for row in left_rows:
        left_by_sig.setdefault(_signature(row), []).append(row)
    right_by_sig = {}
    for row in right_rows:
        right_by_sig.setdefault(_signature(row), []).append(row)

    remaining, resolved, new, severity_changes, confidence_changes = [], [], [], [], []
    for row in left_rows:
        candidates = right_by_sig.get(_signature(row), [])
        match = next((item for item in candidates if abs((item.line_start or 0) - (row.line_start or 0)) <= 3), None)
        if match is None:
            resolved.append(row)
            continue
        remaining.append(row)
        if match.severity != row.severity:
            severity_changes.append({"title": row.title, "from": row.severity, "to": match.severity})
        if abs(match.confidence - row.confidence) >= .05:
            confidence_changes.append({"title": row.title, "from": row.confidence, "to": match.confidence})
    for row in right_rows:
        candidates = left_by_sig.get(_signature(row), [])
        match = next((item for item in candidates if abs((item.line_start or 0) - (row.line_start or 0)) <= 3), None)
        if match is None:
            new.append(row)

    def verdict(before, after, higher_is_better=True):
        if before == after:
            return "unchanged"
        improved = after < before if higher_is_better else after > before
        return "improved" if improved else "regressed"

    return {
        "left": {"id": left.id, "title": left.title, "findings": left.total_findings,
                 "quality": left.quality_score, "risk": left.risk_level, "date": left.created_at.isoformat()},
        "right": {"id": right.id, "title": right.title, "findings": right.total_findings,
                  "quality": right.quality_score, "risk": right.risk_level, "date": right.created_at.isoformat()},
        "counts": {
            "new": len(new), "resolved": len(resolved), "remaining": len(remaining),
            "severity_changes": len(severity_changes), "confidence_changes": len(confidence_changes),
        },
        "verdicts": {
            "total_findings": verdict(left.total_findings, right.total_findings, False),
            "quality_score": verdict(left.quality_score, right.quality_score, True),
            "risk_level": verdict({"Low": 0, "Medium": 1, "High": 2, "Critical": 3}.get(left.risk_level, 0),
                                  {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}.get(right.risk_level, 0), False),
        },
        "new_findings": [{"title": item.title, "severity": item.severity, "rule_id": item.rule_id,
                          "file_name": item.file_name, "line": item.line_start} for item in new],
        "resolved_findings": [{"title": item.title, "severity": item.severity, "rule_id": item.rule_id,
                               "file_name": item.file_name, "line": item.line_start} for item in resolved],
        "remaining_findings": [{"title": item.title, "severity": item.severity, "rule_id": item.rule_id,
                                "file_name": item.file_name, "line": item.line_start} for item in remaining],
        "severity_changes": severity_changes,
        "confidence_changes": confidence_changes,
    }
