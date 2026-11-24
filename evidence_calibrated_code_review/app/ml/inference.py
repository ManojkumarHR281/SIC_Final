"""Model inference for review submissions and vulnerability descriptions."""
import json

from app.ml.calibration import entropy_uncertainty
from app.ml.model_registry import MODEL_DIR, load_model, model_info


def predict_code(code, language):
    if language not in {"c", "cpp"}:
        return {"available": False, "reason": "The trained Devign model is trained on C/C++ functions; this language is unsupported."}
    bundle = load_model("code")
    if bundle is None:
        return {"available": False, "reason": "Code model not trained. Prepare Devign data and run training/train_models.py."}
    source = code[:50000]
    vector = bundle["vectorizer"].transform([source])
    classifier = bundle["classifier"]
    score = classifier.decision_function(vector)
    probability = float(bundle["calibrator"].predict(score)[0])
    uncertainty = entropy_uncertainty(probability)
    metrics_path = MODEL_DIR / "code" / "metrics.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.is_file() else {}
    auc = metrics.get("roc_auc")
    weak_model = auc is not None and auc < .60
    if weak_model or max(probability, 1 - probability) < .60:
        label = "uncertain"
    else:
        label = "vulnerable" if probability >= .5 else "non-vulnerable"
    if weak_model:
        uncertainty = max(uncertainty, .85)
    result = {"available": True, "prediction": label, "model": "TF-IDF + Logistic Regression",
            "version": bundle["version"], "model_probability": float(classifier.predict_proba(vector)[0][1]),
            "calibrated_probability": probability, "uncertainty": uncertainty,
            "vulnerability_type": "Defect/vulnerability (Devign binary label)", "cwe": None,
            "language_scope": "C/C++", "evidence_completeness": "whole submission, capped at 50,000 characters; no line-level attribution"}
    if weak_model:
        result["quality_warning"] = f"Held-out ROC-AUC was {auc:.3f}; the model showed weak separation on the repository holdout, so this result is reported as uncertain."
    return result


def classify_description(description):
    bundle = load_model("nlp")
    if bundle is None:
        return {"available": False, "reason": "NVD text model not trained. Prepare NVD CWE pairs and run training/train_models.py."}
    vector = bundle["vectorizer"].transform([description[:10000]])
    classifier = bundle["classifier"]
    probabilities = classifier.predict_proba(vector)[0]
    index = int(probabilities.argmax())
    return {"available": True, "cwe": str(classifier.classes_[index]), "probability": float(probabilities[index]),
            "top_predictions": [{"cwe": str(classifier.classes_[i]), "probability": float(probabilities[i])}
                                for i in probabilities.argsort()[::-1][:5]],
            "model": "TF-IDF + Logistic Regression", "version": bundle["version"],
            "probabilities_calibrated": False, "source": "NVD CVE descriptions paired with NVD-assigned CWE labels"}


def status():
    return model_info()
