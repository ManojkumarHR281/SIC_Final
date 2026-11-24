import io
import json
import re

import pytest

from app import create_app, db
from app.services.code_analyzer import analyze_python
from app.services.review_engine import review_code
from app.services.security_analyzer import analyze_security
from app.services.evidence_engine import build_evidence
from app.services.uncertainty_engine import calculate_uncertainty
from app.utils.confidence_calculator import calculate_confidence
from app.utils.validators import validate_review, safe_filename, MAX_CODE_BYTES


@pytest.fixture
def client():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"})
    with app.test_client() as client:
        yield client
    with app.app_context():
        db.drop_all()


def csrf_token(page):
    match = re.search(rb'name="csrf_token" value="([^"]+)"', page.data)
    assert match
    return match.group(1).decode()


def test_ast_detects_attribute_based_dangerous_calls():
    code = 'import os, pickle\nos.system("ls")\nos.popen("ls")\npickle.loads(b"x")\n'
    titles = {f["title"] for f in analyze_python(code)}
    assert "Shell command construction" in titles
    assert "Unsafe deserialization" in titles


def test_ast_detects_concatenated_sql_in_execute_call():
    code = 'cursor.execute("SELECT * FROM t WHERE id=" + user_id)\n'
    assert any(f["title"] == "Possible SQL injection" for f in analyze_python(code))


def test_identity_comparison_fix_is_useful():
    finding = next(f for f in analyze_python("if x is 3:\n    pass\n") if f["title"] == "Identity comparison with a literal")
    assert "== 3" in finding["suggested_fix"]
    assert "== None" not in finding["suggested_fix"]


def test_multiline_shell_true_is_detected():
    code = 'subprocess.run(\n    "ls",\n    shell=True,\n)\n'
    assert any(f["title"] == "Subprocess with shell=True" for f in analyze_security(code))


def test_evidence_builder_and_scores_are_normalized():
    evidence = build_evidence("rules", "desc", .9, True)
    assert evidence["source"] == "rules"
    assert evidence["evidence_type"] == "static_analysis"
    assert evidence["verified"] is True
    assert all(0 <= f["confidence"] <= 1 and 0 <= f["uncertainty"] <= 1 for f in review_code("x=1"))
    assert calculate_uncertainty(1.4) == 0.0
    assert calculate_uncertainty(-0.4) == 1.0
    assert calculate_confidence({}) == .15


def test_validation_rejects_wrong_types_and_bad_filenames():
    assert validate_review("x=1", ["python"], "comprehensive", "balanced")
    assert validate_review("x=1", "python", ["bugs"], "balanced")
    assert validate_review("x=1", "python", "comprehensive", ["balanced"])
    assert validate_review("x" * (MAX_CODE_BYTES + 1), "python", "comprehensive", "balanced")
    assert safe_filename(None) == "source.py"
    assert safe_filename("..\\..\\bad name.py") == "bad_name.py"


def test_all_pages_render_and_csrf_form_flow(client):
    for path in ["/", "/review/new", "/history", "/settings"]:
        assert client.get(path).status_code == 200
    page = client.get("/review/new")
    response = client.post("/review/new", data={
        "csrf_token": csrf_token(page),
        "code": 'x = eval(input())\n',
        "title": "CSRF flow",
        "language": "python",
        "mode": "comprehensive",
        "sensitivity": "balanced",
    })
    assert response.status_code == 302
    results = client.get(response.headers["Location"])
    assert results.status_code == 200
    assert b"finding-card" in results.data
    assert b"Evidence and scoring rationale" in results.data
    assert b"\xc3\x82" not in results.data


def test_upload_validation_and_api_reject_malformed_payloads(client):
    page = client.get("/review/new")
    bad = client.post("/review/new", data={
        "csrf_token": csrf_token(page),
        "file": (io.BytesIO(b"x=1"), "bad.exe"),
        "language": "python", "mode": "comprehensive", "sensitivity": "balanced",
    }, content_type="multipart/form-data")
    assert bad.status_code == 302
    assert bad.headers["Location"].endswith("/review/new")
    assert client.post("/api/review", json={"code": "x=1", "language": ["python"]}).status_code == 400
    assert client.post("/api/review", json={"code": ["x"]}).status_code == 400


def test_exports_match_persisted_findings(client):
    created = client.post("/api/review", json={"code": 'eval(input())\nos.system("ls")\n', "language": "python"})
    assert created.status_code == 201
    rid = created.json["id"]
    exported = json.loads(client.get(f"/reviews/{rid}/export/json").data)
    assert exported["total_findings"] == len(exported["findings"])
    assert exported["findings"]
    assert all(f["evidence"] for f in exported["findings"])
    csv_response = client.get(f"/reviews/{rid}/export/csv")
    assert csv_response.status_code == 200
    assert len(csv_response.data.decode().splitlines()) == len(exported["findings"]) + 1
    report = client.get(f"/reviews/{rid}/report")
    assert report.status_code == 200 and report.mimetype == "text/markdown"
    report_text = report.data.decode()
    assert exported["findings"][0]["title"] in report_text
    assert re.search(r"confidence \d+%", report_text)
