"""Probability calibration utilities and evaluation metrics."""
import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss


def expected_calibration_error(y, p, bins=10):
    y, p = np.asarray(y), np.asarray(p)
    edges = np.linspace(0, 1, bins + 1)
    error = 0.0
    for i in range(bins):
        mask = (p >= edges[i]) & ((p <= edges[i + 1]) if i == bins - 1 else (p < edges[i + 1]))
        if mask.any():
            error += float(mask.mean() * abs(y[mask].mean() - p[mask].mean()))
    return float(error)


class ProbabilityCalibrator:
    """Compare sigmoid/Platt and isotonic on held-out validation scores."""
    def fit(self, scores, labels):
        scores, labels = np.asarray(scores), np.asarray(labels)
        if len(np.unique(labels)) < 2 or len(labels) < 20:
            raise ValueError("Calibration needs at least 20 validation rows from both classes.")
        self.platt = LogisticRegression(random_state=42).fit(scores.reshape(-1, 1), labels)
        self.isotonic = IsotonicRegression(out_of_bounds="clip").fit(scores, labels)
        candidates = {"platt": self.platt.predict_proba(scores.reshape(-1, 1))[:, 1],
                      "isotonic": self.isotonic.predict(scores)}
        self.method = min(candidates, key=lambda key: brier_score_loss(labels, candidates[key]))
        self.comparison = {key: {"brier_score": float(brier_score_loss(labels, p)),
                                 "ece": expected_calibration_error(labels, p)} for key, p in candidates.items()}
        return self

    def predict(self, scores):
        scores = np.asarray(scores)
        if self.method == "isotonic":
            return self.isotonic.predict(scores)
        return self.platt.predict_proba(scores.reshape(-1, 1))[:, 1]


def entropy_uncertainty(probability):
    p = float(np.clip(probability, 1e-12, 1 - 1e-12))
    return float(-(p * np.log2(p) + (1 - p) * np.log2(1 - p)))
