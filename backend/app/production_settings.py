import os
from dataclasses import dataclass


TRUE_VALUES = {"1", "true", "yes", "on"}
LOCAL_ORIGINS = {"http://localhost:3000", "http://127.0.0.1:3000"}


@dataclass(frozen=True)
class ProductionSettingsError(RuntimeError):
    issues: tuple[str, ...]

    def __str__(self) -> str:
        return "Unsafe production settings: " + "; ".join(self.issues)


def enabled(value: str | None) -> bool:
    return (value or "").strip().lower() in TRUE_VALUES


def production_mode() -> bool:
    return os.getenv("APP_ENV", "development").strip().lower() in {"production", "prod"}


def configured_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ALLOW_ORIGINS", "")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def validate_production_settings() -> None:
    if not production_mode():
        return

    issues: list[str] = []
    database_url = os.getenv("DATABASE_URL", "")
    cors_origins = configured_cors_origins()

    if not database_url:
        issues.append("DATABASE_URL is required")
    elif database_url.startswith("sqlite"):
        issues.append("sqlite is not allowed when APP_ENV=production")

    if not enabled(os.getenv("REQUIRE_TENANT_HEADER")):
        issues.append("REQUIRE_TENANT_HEADER must be enabled")

    if not enabled(os.getenv("REQUIRE_TRUSTED_INGRESS")):
        issues.append("REQUIRE_TRUSTED_INGRESS must be enabled")

    if not cors_origins:
        issues.append("CORS_ALLOW_ORIGINS must be explicit")
    elif any(origin in LOCAL_ORIGINS for origin in cors_origins):
        issues.append("localhost CORS origins are not allowed when APP_ENV=production")

    if issues:
        raise ProductionSettingsError(tuple(issues))
