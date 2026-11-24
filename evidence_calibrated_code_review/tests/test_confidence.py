from app.utils.confidence_calculator import calculate_confidence, classify_confidence
from app.services.uncertainty_engine import calculate_uncertainty


def test_available_weights_renormalize_and_missing_evidence_is_penalized():
    complete = calculate_confidence({"reliability": .9, "strength": .9, "certainty": .9, "context": .9, "independent": .9})
    sparse = calculate_confidence({"reliability": .9})
    assert complete == .9
    assert sparse < complete


def test_classification_and_uncertainty():
    assert classify_confidence(.8) == "HIGH"
    assert classify_confidence(.5) == "MEDIUM"
    assert classify_confidence(.49) == "LOW"
    assert calculate_uncertainty(.7, context_missing=True) > .3
