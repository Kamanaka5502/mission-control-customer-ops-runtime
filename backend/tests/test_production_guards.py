from fastapi.testclient import TestClient

from app.main import app
from app.services.rbac import Role, create_auth_token

client = TestClient(app)
TEST_SECRET = "0123456789abcdef0123456789abcdef"


def auth_headers(role: Role, actor_id: str = "production-test") -> dict[str, str]:
    token = create_auth_token(actor_id=actor_id, role=role, secret=TEST_SECRET)
    return {"authorization": f"Bearer {token}"}


def enable_production_auth(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    monkeypatch.setenv("AUTH_TOKEN_SECRET", TEST_SECRET)


def test_production_mode_requires_trusted_ingress(monkeypatch):
    enable_production_auth(monkeypatch)

    response = client.get(
        "/ops/customers",
        headers={**auth_headers(Role.AUDITOR), "x-tenant-id": "tenant-a"},
    )

    assert response.status_code == 401
    assert response.json()["detail"]["access"] == "DENIED"


def test_production_mode_requires_bearer_auth_after_verified_ingress(monkeypatch):
    enable_production_auth(monkeypatch)

    response = client.get(
        "/ops/customers",
        headers={"x-ingress-verified": "true", "x-tenant-id": "tenant-a"},
    )

    assert response.status_code == 401
    assert response.json()["detail"]["access"] == "DENIED"
    assert response.json()["detail"]["reason"] == "Bearer token required"


def test_production_mode_requires_tenant_header(monkeypatch):
    enable_production_auth(monkeypatch)

    response = client.get(
        "/ops/customers",
        headers={**auth_headers(Role.AUDITOR), "x-ingress-verified": "true"},
    )

    assert response.status_code == 401
    assert response.json()["detail"]["access"] == "DENIED"


def test_production_mode_accepts_verified_ingress_and_bearer_identity(monkeypatch):
    enable_production_auth(monkeypatch)

    response = client.get(
        "/ops/customers",
        headers={
            **auth_headers(Role.AUDITOR),
            "x-ingress-verified": "true",
            "x-tenant-id": "tenant-a",
        },
    )

    assert response.status_code == 200
