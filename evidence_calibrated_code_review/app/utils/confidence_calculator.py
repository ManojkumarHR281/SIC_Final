"""Reproducible, evidence-weighted confidence scoring (not statistical calibration)."""
WEIGHTS = {"reliability": .30, "strength": .25, "certainty": .20, "context": .15, "independent": .10}
LABELS = {
    "reliability": "Rule reliability",
    "strength": "Evidence strength",
    "certainty": "Detection certainty",
    "context": "Context completeness",
    "independent": "Independent confirmation",
}


def _bounded(value):
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def calculate_confidence(factors, deterministic=False):
    available = {key: _bounded(value) for key, value in factors.items() if value is not None and key in WEIGHTS}
    if not available:
        return .15
    denominator = sum(WEIGHTS[key] for key in available)
    score = sum(WEIGHTS[key] * value for key, value in available.items()) / denominator
    score *= .75 + .25 * (len(available) / len(WEIGHTS))
    if deterministic:
        score = max(score, .82)
    return round(max(0.0, min(1.0, score)), 4)


def classify_confidence(score):
    value = _bounded(score)
    return "HIGH" if value >= .8 else "MEDIUM" if value >= .5 else "LOW"


def confidence_factors(factors, deterministic=False):
    """Human-readable contribution breakdown for a computed score."""
    available = {key: _bounded(value) for key, value in factors.items() if value is not None and key in WEIGHTS}
    denominator = sum(WEIGHTS[key] for key in available) or 1.0
    rows = []
    for key, weight in WEIGHTS.items():
        if key in available:
            rows.append({
                "factor": key, "label": LABELS[key], "weight": weight,
                "value": round(available[key], 3),
                "contribution": round(weight * available[key] / denominator, 3),
                "available": True,
            })
        else:
            rows.append({
                "factor": key, "label": LABELS[key], "weight": weight,
                "value": None, "contribution": 0.0, "available": False,
            })
    return {"rows": rows, "deterministic_floor": .82 if deterministic else None,
            "completeness": round(len(available) / len(WEIGHTS), 3)}
