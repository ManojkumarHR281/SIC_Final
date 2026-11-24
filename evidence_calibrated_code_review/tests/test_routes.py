import pytest
from app import create_app, db


@pytest.fixture
def client():
    app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False, "SQLALCHEMY_DATABASE_URI": "sqlite://"})
    with app.test_client() as client:
        yield client
    with app.app_context():
        db.drop_all()


def test_dashboard_and_review_api_persistence_exports(client):
    assert client.get("/").status_code == 200
    bad = client.post("/api/review", json={"code": "  "})
    assert bad.status_code == 400
    result = client.post("/api/review", json={"code": "x = eval(input())", "language": "python"})
    assert result.status_code == 201
    review_id = result.json["id"]
    assert client.get("/api/reviews").status_code == 200
    assert client.get(f"/api/reviews/{review_id}").status_code == 200
    assert client.get(f"/reviews/{review_id}/export/csv").status_code == 200
    assert client.get(f"/reviews/{review_id}/export/json").status_code == 200
    assert client.get("/history").status_code == 200
    assert client.get("/api/dashboard/stats").json["total_reviews"] == 1


def test_delete_review(client):
    result = client.post("/api/review", json={"code": "x = 1", "language": "python"})
    from app.models import Review
    response = client.post(f"/reviews/{result.json['id']}/delete")
    assert response.status_code == 302
    assert Review.query.count() == 0
