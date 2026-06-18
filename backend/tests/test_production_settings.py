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
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://example")
    monkeypatch.setenv("REQUIRE_TENANT_HEADER", "true")
    monkeypatch.setenv("REQUIRE_TRUSTED_INGRESS", "true")
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", origin)

    with pytest.raises(ProductionSettingsError) as exc:
        validate_production_settings()

    assert "localhost CORS origins are not allowed" in str(exc.value)


def test_production_settings_accept_hardened_configuration(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://example")
    monkeypatch.setenv("REQUIRE_TENANT_HEADER", "true")
    monkeypatch.setenv("REQUIRE_TRUSTED_INGRESS", "true")
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "https://app.example.com")

    validate_production_settings()
