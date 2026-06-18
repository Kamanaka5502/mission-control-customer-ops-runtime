import pytest

from app.production_settings import ProductionSettingsError, validate_production_settings


def set_base_production_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://example")
    monkeypatch.setenv("REQUIRE_TENANT_HEADER", "true")
    monkeypatch.setenv("REQUIRE_TRUSTED_INGRESS", "true")
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    monkeypatch.setenv("AUTH_TOKEN_SECRET", "0123456789abcdef0123456789abcdef")
    monkeypatch.setenv("RECEIPT_SIGNING_KEY_ID", "receipt-key-test")
    monkeypatch.setenv("RECEIPT_SIGNING_SECRET", "receipt-signing-secret-0123456789abcdef")
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "https://app.example.com")


def test_production_settings_reject_sqlite(monkeypatch):
    set_base_production_env(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///local.db")

    with pytest.raises(ProductionSettingsError) as exc:
        validate_production_settings()

    assert "sqlite is not allowed" in str(exc.value)


def test_production_settings_require_explicit_cors(monkeypatch):
    set_base_production_env(monkeypatch)
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)

    with pytest.raises(ProductionSettingsError) as exc:
        validate_production_settings()

    assert "CORS_ALLOW_ORIGINS must be explicit" in str(exc.value)


@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost",
        "http://localhost:5173",
        "http://127.0.0.1:8000",
        "http://0.0.0.0:3000",
    ],
)
def test_production_settings_reject_local_cors_hosts(monkeypatch, origin):
    set_base_production_env(monkeypatch)
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", origin)

    with pytest.raises(ProductionSettingsError) as exc:
        validate_production_settings()

    assert "localhost CORS origins are not allowed" in str(exc.value)


@pytest.mark.parametrize(
    "secret",
    [
        "change-me",
        "replace_with_32_plus_character_random_secret",
        "short-secret",
        "",
    ],
)
def test_production_startup_refuses_default_or_sample_secret(monkeypatch, secret):
    set_base_production_env(monkeypatch)
    monkeypatch.setenv("AUTH_TOKEN_SECRET", secret)

    with pytest.raises(ProductionSettingsError) as exc:
        validate_production_settings()

    assert "AUTH_TOKEN_SECRET" in str(exc.value)


@pytest.mark.parametrize(
    "secret",
    [
        "development-receipt-secret-not-for-production",
        "short-secret",
        "",
    ],
)
def test_production_startup_refuses_default_receipt_signing_secret(monkeypatch, secret):
    set_base_production_env(monkeypatch)
    monkeypatch.setenv("RECEIPT_SIGNING_SECRET", secret)

    with pytest.raises(ProductionSettingsError) as exc:
        validate_production_settings()

    assert "RECEIPT_SIGNING_SECRET" in str(exc.value)


def test_production_settings_require_auth(monkeypatch):
    set_base_production_env(monkeypatch)
    monkeypatch.setenv("AUTH_REQUIRED", "false")

    with pytest.raises(ProductionSettingsError) as exc:
        validate_production_settings()

    assert "AUTH_REQUIRED must be enabled" in str(exc.value)


def test_production_settings_accept_hardened_configuration(monkeypatch):
    set_base_production_env(monkeypatch)

    validate_production_settings()
