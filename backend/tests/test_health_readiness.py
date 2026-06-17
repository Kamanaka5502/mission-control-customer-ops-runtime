from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_returns_service_metadata(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "mission-control-customer-ops-runtime"
    assert body["environment"] == "test"


def test_readiness_checks_database():
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["database"] == "available"
