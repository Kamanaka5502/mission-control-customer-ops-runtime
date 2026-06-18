import os
from dataclasses import dataclass
from urllib.parse import urlparse


TRUE_VALUES = {"1", "true", "yes", "on"}
LOCAL_CORS_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
DEFAULT_SECRET_VALUES = {
    "",
    "change-me",
    "changeme",
    "dev-secret",
    "default",
    "secret",
    "replace_with_32_plus_character_random_secret",
}


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


def is_local_cors_origin(origin: str) -> bool:
    parsed = urlparse(origin.strip())
    host = (parsed.hostname or "").lower()
    return host in LOCAL_CORS_HOSTS


def valid_auth_secret(value: str | None) -> bool:
    secret = (value or "").strip()
    return secret.lower() not in DEFAULT_SECRET_VALUES and len(secret) >= 32


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

    if not enabled(os.getenv("AUTH_REQUIRED")):
        issues.append("AUTH_REQUIRED must be enabled")

    if not valid_auth_secret(os.getenv("AUTH_TOKEN_SECRET")):
        issues.append("AUTH_TOKEN_SECRET must be set to a non-default value of at least 32 characters")

    if not cors_origins:
        issues.append("CORS_ALLOW_ORIGINS must be explicit")
    elif any(is_local_cors_origin(origin) for origin in cors_origins):
        issues.append("localhost CORS origins are not allowed when APP_ENV=production")

    if issues:
        raise ProductionSettingsError(tuple(issues))
