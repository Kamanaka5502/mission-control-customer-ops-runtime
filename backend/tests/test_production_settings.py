import pytest

from app.production_settings import ProductionSettingsError, validate_production_settings


def test_production_settings_reject_sqlite(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///local.db")
    monkeypatch.setenv("REQUIRE_TENANT_HEADER", "true")
    monkeypatch.setenv("REQUIRE_TRUSTED_INGRESS", "true")
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "https://app.example.com")

    with pytest.raises(ProductionSettingsError) as exc:
        validate_production_settings()

    assert "sqlite is not allowed" in str(exc.value)


def test_production_settings_require_explicit_cors(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://example")
    monkeypatch.setenv("REQUIRE_TENANT_HEADER", "true")
    monkeypatch.setenv("REQUIRE_TRUSTED_INGRESS", "true")
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)

    with pytest.raises(ProductionSettingsError) as exc:
        validate_production_settings()

    assert "CORS_ALLOW_ORIGINS must be explicit" in str(exc.value)


def test_production_settings_accept_hardened_configuration(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://example")
    monkeypatch.setenv("REQUIRE_TENANT_HEADER", "true")
    monkeypatch.setenv("REQUIRE_TRUSTED_INGRESS", "true")
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "https://app.example.com")

    validate_production_settings()
