from app.utils.validators import validate_review, safe_filename


def test_validation_and_filename_sanitization():
    assert validate_review(" ", "python", "comprehensive", "balanced")
    assert validate_review("print(1)", "bad", "comprehensive", "balanced")
    assert validate_review("print(1)", "python", "comprehensive", "balanced") is None
    assert safe_filename("../../secret.py") == "secret.py"
