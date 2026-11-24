"""Load locally trained models; absent models are an explicit state."""
import json
from pathlib import Path

import joblib

from config import BASE_DIR

MODEL_DIR = BASE_DIR / "trained_models"


def model_info():
    result = {}
    for name in ("code", "nlp"):
        path = MODEL_DIR / name
        meta = path / "metrics.json"
        artifact = path / "model.joblib"
        result[name] = {"trained": artifact.is_file(), "model": "TF-IDF + Logistic Regression",
                        "version": "1.0" if artifact.is_file() else None,
                        "metrics": json.loads(meta.read_text(encoding="utf-8")) if meta.is_file() else None}
    return result


def load_model(name):
    artifact = MODEL_DIR / name / "model.joblib"
    if not artifact.is_file():
        return None
    return joblib.load(artifact)
