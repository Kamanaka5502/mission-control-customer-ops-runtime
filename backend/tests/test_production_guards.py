from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_production_mode_requires_explicit_actor_role(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")

    response = client.get("/ops/customers", headers={"x-tenant-id": "tenant-a"})

    assert response.status_code == 401
    assert response.json()["detail"]["access"] == "DENIED"


def test_production_mode_requires_tenant_header(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")

    response = client.get("/ops/customers", headers={"x-actor-role": "auditor"})

    assert response.status_code == 401
    assert response.json()["detail"]["access"] == "DENIED"
