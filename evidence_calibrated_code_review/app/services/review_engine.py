"""Coordinates language analyzers, evidence, scoring and quality metrics."""
from app.services.analyzer_registry import analyze
from app.services.ai_provider import ACTIONS  # noqa: F401 - exported for API discovery
from app.services.evidence_engine import build_evidence
from app.services.fix_engine import validate_fix
from app.services.uncertainty_engine import calculate_uncertainty
from app.utils.confidence_calculator import calculate_confidence, classify_confidence, confidence_factors

SEVERITY_RANK = {"Critical": 5, "High": 4, "Medium": 3, "Low": 2, "Informational": 1}
SEVERITY_PENALTY = {"Critical": 20, "High": 10, "Medium": 5, "Low": 2, "Informational": 0}
MODE_CATEGORIES = {
    "bugs": {"Bug", "Syntax"},
    "security": {"Security"},
    "performance": {"Performance"},
    "quality": {"Quality"},
}


class ReviewResult(list):
    """A findings list that also carries project-level analysis metadata."""

    def __init__(self, items, metrics, quality_score, risk_level):
        super().__init__(items)
        self.metrics = metrics
        self.quality_score = quality_score
        self.risk_level = risk_level


def _quality_score(findings, metrics):
    penalty = sum(SEVERITY_PENALTY.get(item["severity"], 0) * (.5 + item["confidence"] * .5) for item in findings)
    penalty += max(0, metrics.get("max_complexity", 0) - 8) * 1.5
    penalty += max(0, metrics.get("max_nesting", 0) - 4) * 2
    return round(max(0.0, min(100.0, 100 - penalty)), 1)


def _risk_level(findings):
    high_confirmed = [f for f in findings if f["severity"] in {"High", "Critical"} and f["confidence"] >= .7]
    if any(f["severity"] == "Critical" and f["confidence"] >= .7 for f in findings):
        return "Critical"
    if len(high_confirmed) >= 2:
        return "High"
    if high_confirmed or sum(1 for f in findings if f["severity"] == "Medium") >= 3:
        return "Medium"
    return "Low"


def review_code(code, language="python", mode="comprehensive", sensitivity="balanced", file_name="submitted_code.py"):
    raw, metrics, full_analysis = analyze(code, language)
    from app.ml.inference import predict_code
    ml_prediction = predict_code(code, language)
    # When a matching, trained corpus model is available it owns vulnerability
    # classification. Existing analyzers continue to cover non-security quality
    # findings and languages outside the model's stated scope.
    if ml_prediction.get("available"):
        raw = [item for item in raw if item.get("category") != "Security"]
    if mode in MODE_CATEGORIES:
        raw = [item for item in raw if item.get("category") in MODE_CATEGORIES[mode]]

    results = []
    seen = set()
    for item in raw:
        identifier = item.get("rule_id") or item.get("title", "")
        key = (identifier, item.get("line", 1), item.get("column", 1), file_name)
        if key in seen:
            continue
        seen.add(key)
        factors = {name: item.get(name) for name in ("reliability", "strength", "certainty", "context", "independent")}
        confidence = calculate_confidence(factors, item.get("verified", False))
        if sensitivity == "conservative" and confidence < .68:
            continue
        uncertainty = calculate_uncertainty(
            confidence,
            context_missing=item.get("context", 0) < .7,
            context_dependent=item.get("context_dependent", False),
            context_completeness=item.get("context"),
            detection_certainty=item.get("certainty"),
        )
        explanation = confidence_factors(factors, item.get("verified", False))
        fix = validate_fix(item.get("suggested_fix", ""), language)
        rationale_parts = []
        for row in explanation["rows"]:
            value_text = f"{row['value']:.0%}" if row["available"] else "unavailable"
            rationale_parts.append(f"{row['label']}: {value_text}")
        rationale = (
            "Evidence-weighted estimate (" + ", ".join(rationale_parts) + "). "
            + ("A deterministic floor of 82% applies to verified syntactic observations. " if item.get("verified") else "")
            + "These are heuristic estimates, not empirically calibrated probabilities."
        )
        item.update(
            confidence=confidence,
            uncertainty=uncertainty,
            confidence_level=classify_confidence(confidence),
            rule_id=identifier,
            file_name=file_name,
            explanation=item.get("explanation") or item.get("description", ""),
            score_factors=explanation,
            rationale=rationale,
            fix_code=item.get("suggested_fix", ""),
            fix_valid=fix["syntax_valid"],
            evidence=[build_evidence(item["source"], item.get("evidence_description", item.get("description", "")), item["strength"], item["verified"])],
            snippet=item.get("snippet", ""),
            limited_analysis=not full_analysis,
        )
        if item["severity"] in {"High", "Critical"} and confidence < .5:
            item["warning"] = "Potentially serious issue, but supporting evidence is weak. Manual verification is strongly recommended."
        results.append(item)

    if (ml_prediction.get("available") and ml_prediction["prediction"] in {"vulnerable", "uncertain"}
            and (mode not in MODE_CATEGORIES or "Security" in MODE_CATEGORIES[mode])):
        probability = ml_prediction["calibrated_probability"]
        if sensitivity == "conservative" and probability < .68:
            probability = None
        if probability is not None:
            uncertain = ml_prediction["prediction"] == "uncertain"
            explanation_text = (("The model result is uncertain and should be manually reviewed. " + ml_prediction.get("quality_warning", "") +
                                 " Devign supplies only a binary label; it does not support a specific CWE or line attribution.") if uncertain else
                                "The trained Devign classifier marked this C/C++ submission as a potential defect/vulnerability. The dataset supplies only a binary label; it does not support a specific CWE or line attribution.")
            results.append({
                "title": "ML model: potential code vulnerability" if not uncertain else "ML model: uncertain classification",
                "description": explanation_text, "category": "Security",
                "severity": "High" if not uncertain else "Informational", "line": None, "column": None,
                "snippet": "", "source": "CodeXGLUE Devign trained model", "strength": .5,
                "verified": False, "reliability": None, "certainty": probability, "context": None,
                "rule_id": "ML-DEVIGN", "cwe": "", "category_group": "Defect/vulnerability",
                "explanation": explanation_text,
                "recommendation": "Manually inspect the affected function and validate the behavior against application context; this model does not provide an automated fix.",
                "suggested_fix": "", "potential_impact": "A model signal alone does not establish exploitability or runtime impact.",
                "confidence": probability, "uncertainty": ml_prediction["uncertainty"],
                "confidence_level": classify_confidence(probability), "file_name": file_name,
                "rationale": f"Calibrated held-out validation probability using {ml_prediction['model']} ({ml_prediction['version']}); entropy-based uncertainty. No line attribution available.",
                "fix_code": "", "fix_valid": False, "evidence": [build_evidence("CodeXGLUE Devign model", "Whole submitted C/C++ text was classified by a trained defect model.", .5, False)],
                "model_probability": ml_prediction["model_probability"],
                "calibrated_probability": ml_prediction["calibrated_probability"], "model_version": ml_prediction["version"],
            })

    results.sort(key=lambda f: (SEVERITY_RANK.get(f["severity"], 0), f["confidence"], f.get("strength", 0)), reverse=True)
    metrics = dict(metrics)
    metrics["full_analysis"] = full_analysis
    metrics["ml_prediction"] = ml_prediction
    metrics["model_info"] = __import__("app.ml.model_registry", fromlist=["model_info"]).model_info()
    return ReviewResult(results, metrics, _quality_score(results, metrics), _risk_level(results))
