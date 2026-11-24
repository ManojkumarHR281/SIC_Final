import numpy as np

from app.ml.calibration import ProbabilityCalibrator, entropy_uncertainty, expected_calibration_error
from app.ml.dataset_loader import clean_code_records, clean_cve_records


def test_dataset_cleaning_drops_invalid_exact_and_near_duplicate_code():
    rows = [
        {"code": "int add(int x, int y) { return x + y; }", "label": 0, "project": "a"},
        {"code": "int  add ( int x , int y ) { return x + y ; }", "label": 1, "project": "b"},
        {"code": "short", "label": 0, "project": "a"},
        {"code": "int f(){ return 1; }", "label": "bad", "project": "a"},
    ]
    assert len(clean_code_records(rows)) == 1


def test_cve_cleaner_requires_usable_text_and_cwe():
    rows = [{"description": "An overflow in a parser can cause memory corruption.", "cwe": "CWE-120"},
            {"description": "No CWE is available in this record.", "cwe": "NVD-CWE-noinfo"},
            {"description": "tiny", "cwe": "CWE-89"}]
    cleaned = clean_cve_records(rows)
    assert len(cleaned) == 1 and cleaned[0]["label"] == "CWE-120"


def test_calibration_compares_methods_and_entropy_is_not_one_minus_probability():
    labels = np.array([0, 1] * 30)
    scores = np.array([-2.0, 1.5] * 30)
    calibrator = ProbabilityCalibrator().fit(scores, labels)
    values = calibrator.predict(np.array([-2.0, 1.5]))
    assert calibrator.method in {"platt", "isotonic"}
    assert set(calibrator.comparison) == {"platt", "isotonic"}
    assert np.all((values >= 0) & (values <= 1))
    assert 0 <= entropy_uncertainty(.5) <= 1
    assert entropy_uncertainty(.5) > entropy_uncertainty(.99)
    assert expected_calibration_error([0, 1], [.1, .9]) < .2
