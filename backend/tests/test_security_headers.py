from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_security_headers_are_present_on_health_response():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Cross-Origin-Opener-Policy"] == "same-origin"


def test_sensitive_runtime_routes_are_not_cached():
    response = client.post("/ops/customers", json={"name": "Example", "industry": "test"})

    assert response.headers["Cache-Control"] == "no-store"
