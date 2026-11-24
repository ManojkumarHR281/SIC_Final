"""Uncertainty estimation separate from, but informed by, confidence."""
from app.utils.confidence_calculator import _bounded


def calculate_uncertainty(confidence, context_missing=False, context_dependent=False,
                          context_completeness=None, detection_certainty=None):
    """Heuristic uncertainty in [0, 1] based on residual doubt and context gaps.

    Confidence contributes 60%, context completeness 25%, and detection certainty
    15%. Missing context and context-dependent behavior add bounded increments.
    """
    confidence = _bounded(confidence)
    if confidence <= 0:
        return 1.0
    residual = (1 - confidence) * .60
    if context_completeness is None:
        context_gap = .10 if context_missing else 0.0
    else:
        context_gap = (1 - _bounded(context_completeness)) * .25
    if detection_certainty is None:
        detection_gap = 0.0
    else:
        detection_gap = (1 - _bounded(detection_certainty)) * .15
    value = residual + context_gap + detection_gap
    if context_missing:
        value += .10
    if context_dependent:
        value += .08
    return round(max(0.0, min(1.0, value)), 4)
