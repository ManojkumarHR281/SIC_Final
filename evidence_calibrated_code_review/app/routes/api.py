"""Utility APIs for AI explanations, fixes, settings and samples."""
from flask import Blueprint, jsonify, request

from app import csrf
from app.models import Review
from app.services.ai_provider import provider_status, request_explanation
from app.services.fix_engine import apply_line_replacement, validate_fix
from app.utils.settings_store import get_settings, save_settings
from app.routes.review import SAMPLES
from app.ml.inference import classify_description, predict_code, status as ml_status
from app.nlp.explanation_generator import explain_code_prediction

bp = Blueprint("api_utils", __name__)
csrf.exempt(bp)


@bp.get("/api/settings")
def api_get_settings():
    return jsonify(get_settings())


@bp.post("/api/settings")
def api_save_settings():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Expected a JSON object."}), 400
    return jsonify(save_settings(payload))


@bp.post("/api/ai/explain")
def api_ai_explain():
    payload = request.get_json(silent=True) or {}
    action = payload.get("action", "explain_code")
    code = payload.get("code", "")
    if not isinstance(code, str) or not code.strip():
        return jsonify({"ok": False, "error": "Source code is required for an AI explanation."}), 400
    finding = payload.get("finding") if isinstance(payload.get("finding"), dict) else None
    result = request_explanation(action, code, finding)
    return jsonify(result), 200 if result["ok"] else 502


@bp.get("/api/ai/status")
def api_ai_status():
    return jsonify(provider_status())


@bp.post("/api/fix/validate")
def api_fix_validate():
    payload = request.get_json(silent=True) or {}
    return jsonify(validate_fix(payload.get("code", ""), payload.get("language", "python")))


@bp.post("/api/fix/apply")
def api_fix_apply():
    payload = request.get_json(silent=True) or {}
    source = payload.get("source", "")
    line = payload.get("line")
    replacement = payload.get("replacement", "")
    patched = apply_line_replacement(source, line, replacement)
    check = validate_fix(patched) if patched else {"valid": False, "reason": "No patched source."}
    return jsonify({"source": patched, "syntax_valid": check["syntax_valid"], "reason": check["reason"]})


@bp.get("/api/samples")
def api_samples():
    return jsonify([{"name": name, "code": code} for name, code in SAMPLES.items()])


@bp.get("/api/integrations")
def api_integrations():
    import os
    token = bool(os.environ.get("GITHUB_TOKEN", "").strip())
    return jsonify({
        "github": {"enabled": False, "configured": token,
                   "reason": "GitHub repository access is not enabled in this offline-first build."},
        "ai": provider_status(),
    })


@bp.get("/api/analytics/summary")
def api_analytics_summary():
    from app.routes.dashboard import stats_data
    return jsonify(stats_data(request.args.get("range", "30")))


@bp.get("/api/ml/info")
def api_ml_info():
    return jsonify(ml_status())


@bp.get("/api/ml/training-status")
def api_ml_training_status():
    models = ml_status()
    return jsonify({"status": "ready" if any(item["trained"] for item in models.values()) else "not_trained",
                    "models": models, "training_is_offline_command": True})


@bp.post("/api/ml/predict")
def api_ml_predict():
    payload = request.get_json(silent=True) or {}
    code, language = payload.get("code", ""), payload.get("language", "c")
    if not isinstance(code, str) or not code.strip():
        return jsonify({"error": "Source code is required."}), 400
    result = predict_code(code, language)
    result["explanation"] = explain_code_prediction(code, result)
    return jsonify(result)


@bp.post("/api/nlp/classify")
def api_nlp_classify():
    payload = request.get_json(silent=True) or {}
    description = payload.get("description", "")
    if not isinstance(description, str) or not description.strip():
        return jsonify({"error": "A vulnerability description is required."}), 400
    result = classify_description(description)
    return jsonify(result)


@bp.post("/api/nlp/explain")
def api_nlp_explain():
    payload = request.get_json(silent=True) or {}
    code, language = payload.get("code", ""), payload.get("language", "c")
    if not isinstance(code, str) or not code.strip():
        return jsonify({"error": "Source code is required."}), 400
    prediction = predict_code(code, language)
    return jsonify({"prediction": prediction, "explanation": explain_code_prediction(code, prediction),
                    "provenance": "Local model output and a grounded deterministic explanation template; no external LLM."})
