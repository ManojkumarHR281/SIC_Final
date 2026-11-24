import pytest

from app import create_app, db
from app.models import Review
from app.utils.settings_store import get_settings


@pytest.fixture
def client():
    app = create_app(dict(TESTING=True, WTF_CSRF_ENABLED=False,
                          SQLALCHEMY_DATABASE_URI="sqlite://"))
    with app.test_client() as test_client:
        yield test_client
    with app.app_context():
        db.drop_all()


def make_review(client, code, title="Review"):
    response = client.post("/api/review", json={
        "code": code, "language": "python", "title": title
    })
    assert response.status_code == 201, response.data
    return response.json["id"]


def test_all_workspace_pages_render(client):
    paths = ["/", "/review/new", "/history", "/settings", "/security", "/quality",
             "/analytics", "/reports", "/compare", "/help"]
    for path in paths:
        response = client.get(path)
        assert response.status_code == 200, (path, response.status_code)


def test_multi_file_review_keeps_digest_by_default(client):
    response = client.post("/api/review", json={
        "language": "python",
        "files": [
            {"name": "auth.py", "code": "import os\nos.system(user_input)\n"},
            {"name": "utils.py", "code": "def add(a, b):\n    return a + b\n"},
        ],
    })
    assert response.status_code == 201
    with client.application.app_context():
        review = db.session.get(Review, response.json["id"])
        assert review.file_count == 2
        assert set(review.file_names) == {"auth.py", "utils.py"}
        assert review.source_files == {}
        assert review.findings


def test_source_retention_requires_explicit_opt_in(client):
    response = client.post("/api/review", json={
        "language": "python", "code": "x = eval(input())", "store_source": True
    })
    assert response.status_code == 201
    with client.application.app_context():
        review = db.session.get(Review, response.json["id"])
        assert review.source_files == {"submitted_code.py": "x = eval(input())"}


def test_ml_apis_report_missing_models_without_mock_predictions(client):
    info = client.get("/api/ml/info")
    assert info.status_code == 200
    code_trained = info.json["code"]["trained"]
    prediction = client.post("/api/ml/predict", json={"code": "int main(){return 0;}", "language": "c"})
    assert prediction.status_code == 200
    assert prediction.json["available"] is code_trained
    if code_trained:
        assert prediction.json["prediction"] in {"vulnerable", "non-vulnerable", "uncertain"}
        assert "calibrated_probability" in prediction.json
    else:
        assert "not trained" in prediction.json["reason"].lower()
    classification = client.post("/api/nlp/classify", json={"description": "An input validation flaw in a server component."})
    assert classification.status_code == 200
    assert classification.json["available"] is info.json["nlp"]["trained"]


def test_comparison_uses_stable_rule_context(client):
    left = make_review(client, "import os\nos.system(user_input)\n", "Before")
    right = make_review(client, "value = 1\n", "After")
    page = client.get(f"/compare?left={left}&right={right}")
    assert page.status_code == 200
    assert b"Resolved findings" in page.data
    data = client.get(f"/api/reviews/compare?left={left}&right={right}").json
    assert data["counts"]["resolved"] >= 1
    assert data["verdicts"]["total_findings"] in {"improved", "unchanged", "regressed"}


def test_settings_form_persists_typed_preferences(client):
    response = client.post("/settings", data={
        "font_size": "16",
        "tab_size": "2",
        "word_wrap": "false",
        "confidence_display": "decimal",
        "default_report_format": "markdown",
        "enabled_rules[security]": "false",
        "report_options[include_snippets]": "false",
    }, follow_redirects=True)
    assert response.status_code == 200
    with client.application.app_context():
        saved = get_settings()
    assert saved["font_size"] == 16
    assert saved["word_wrap"] is False
    assert saved["confidence_display"] == "decimal"
    assert saved["enabled_rules"]["security"] is False
    assert saved["report_options"]["include_snippets"] is False


def test_fix_apis_are_deterministic(client):
    valid = client.post("/api/fix/validate", json={"code": "x = 1\n", "language": "python"}).json
    invalid = client.post("/api/fix/validate", json={"code": "def broken(:\n", "language": "python"}).json
    assert valid["syntax_valid"] is True
    assert invalid["syntax_valid"] is False
    applied = client.post("/api/fix/apply", json={
        "source": "x = 1\ny = 2\n", "line": 2, "replacement": "y = 3"
    }).json
    assert applied["source"] == "x = 1\ny = 3\n"
    assert applied["syntax_valid"] is True


def test_pdf_and_json_exports_match_review(client):
    review_id = make_review(client, "eval(user_input)\n")
    pdf = client.get(f"/reviews/{review_id}/export/pdf")
    assert pdf.status_code == 200
    assert pdf.data.startswith(b"%PDF")
    exported = client.get(f"/reviews/{review_id}/export/json").json
    assert exported["total_findings"] == len(exported["findings"])
    assert exported["findings"]


def test_dashboard_api_exposes_advanced_series(client):
    make_review(client, "eval(user_input)\n")
    stats = client.get("/api/dashboard/stats").json
    assert stats["total_reviews"] == 1
    assert stats["total_issues"] >= 1
    assert "trends" in stats and "timeline" in stats
    assert set(stats["severity"]) >= {"Critical", "High", "Medium", "Low", "Informational"}
    assert set(stats["confidence"]) == {"HIGH", "MEDIUM", "LOW"}


def test_ai_provider_never_fakes_responses(client):
    status = client.get("/api/ai/status").json
    assert status["enabled"] is False
    result = client.post("/api/ai/explain", json={"action": "explain_code", "code": "x = 1"}).json
    assert result["ok"] is False
    assert result["error"]
