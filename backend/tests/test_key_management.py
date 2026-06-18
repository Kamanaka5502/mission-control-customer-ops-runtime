import pytest

from app.models import CustomerRequest, Outcome
from app.production_settings import ProductionSettingsError, validate_production_settings
from app.services.rbac import Role, create_auth_token, verify_auth_token
from app.services.receipt import build_receipt, verify_receipt_signature


AUTH_NOW = "auth-current-material-0123456789abcdef"
AUTH_OLD = "auth-previous-material-0123456789abcdef"
RECEIPT_NOW = "receipt-current-material-0123456789abcdef"
RECEIPT_OLD = "receipt-previous-material-0123456789abcdef"


def demo_request() -> CustomerRequest:
    return CustomerRequest(
        customer_id="key-customer",
        workflow_id="key-workflow",
        request_id="REQ-KEY-001",
        requested_action="approve_key_test_action",
        business_context="Key management test request",
        authority_present=True,
        scope_matched=True,
        evidence_present=True,
        evidence_fresh=True,
        risk_level="low",
        approval_required=False,
        metadata={"purpose": "key-management-test"},
    )


def test_auth_token_verifies_with_previous_material(monkeypatch):
    token = create_auth_token(actor_id="old-service", role=Role.AUDITOR, secret=AUTH_OLD)
    monkeypatch.setenv("AUTH_TOKEN_SECRET", AUTH_NOW)
    monkeypatch.setenv("AUTH_TOKEN_PREVIOUS_SECRETS", AUTH_OLD)

    actor = verify_auth_token(token)

    assert actor.actor_id == "old-service"
    assert actor.role == Role.AUDITOR


def test_receipt_verifies_with_previous_key(monkeypatch):
    monkeypatch.setenv("RECEIPT_SIGNING_KEY_ID", "receipt-key-old")
    monkeypatch.setenv("RECEIPT_SIGNING_SECRET", RECEIPT_OLD)
    receipt = build_receipt(demo_request(), Outcome.ADMIT, "AUTHORIZED_TO_RELEASE", False, ["AUTHORITY_PRESENT"])
    payload = receipt.model_dump(mode="json")

    monkeypatch.setenv("RECEIPT_SIGNING_KEY_ID", "receipt-key-current")
    monkeypatch.setenv("RECEIPT_SIGNING_SECRET", RECEIPT_NOW)
    monkeypatch.setenv("RECEIPT_SIGNING_PREVIOUS_KEYS", f"receipt-key-old:{RECEIPT_OLD}")

    result = verify_receipt_signature(payload)

    assert result["valid"] is True
    assert result["signature_key_id"] == "receipt-key-old"


def test_receipt_requires_known_key(monkeypatch):
    monkeypatch.setenv("RECEIPT_SIGNING_KEY_ID", "receipt-key-old")
    monkeypatch.setenv("RECEIPT_SIGNING_SECRET", RECEIPT_OLD)
    receipt = build_receipt(demo_request(), Outcome.ADMIT, "AUTHORIZED_TO_RELEASE", False, ["AUTHORITY_PRESENT"])
    payload = receipt.model_dump(mode="json")

    monkeypatch.setenv("RECEIPT_SIGNING_KEY_ID", "receipt-key-current")
    monkeypatch.setenv("RECEIPT_SIGNING_SECRET", RECEIPT_NOW)
    monkeypatch.delenv("RECEIPT_SIGNING_PREVIOUS_KEYS", raising=False)

    result = verify_receipt_signature(payload)

    assert result["valid"] is False
    assert result["reason"] == "unknown_signature_key_id"


def test_production_settings_requires_explicit_receipt_key(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://db.example/app")
    monkeypatch.setenv("REQUIRE_TENANT_HEADER", "true")
    monkeypatch.setenv("REQUIRE_TRUSTED_INGRESS", "true")
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    monkeypatch.setenv("AUTH_TOKEN_SECRET", AUTH_NOW)
    monkeypatch.setenv("RECEIPT_SIGNING_KEY_ID", "development-receipt-key")
    monkeypatch.setenv("RECEIPT_SIGNING_SECRET", RECEIPT_NOW)
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "https://app.example.com")

    with pytest.raises(ProductionSettingsError) as exc:
        validate_production_settings()

    assert "RECEIPT_SIGNING_KEY_ID" in str(exc.value)
