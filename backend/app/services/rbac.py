import hmac
import os
from enum import Enum
from fastapi import Header, HTTPException


class Role(str, Enum):
    ADMIN = "admin"
    REVIEWER = "reviewer"
    OPERATOR = "operator"
    AUDITOR = "auditor"


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def runtime_access_required() -> bool:
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    return app_env in {"production", "prod"} or _truthy(os.getenv("REQUIRE_RUNTIME_TOKEN"))


def _configured_runtime_tokens() -> list[str]:
    return [token.strip() for token in os.getenv("RUNTIME_ACCESS_TOKENS", "").split(",") if token.strip()]


def validate_runtime_token(x_runtime_token: str | None):
    if not runtime_access_required():
        return

    tokens = _configured_runtime_tokens()
    if not tokens:
        raise HTTPException(
            status_code=500,
            detail={
                "security": "MISCONFIGURED",
                "reason": "RUNTIME_ACCESS_TOKENS must be configured when production runtime-token enforcement is enabled.",
            },
        )

    if not x_runtime_token or not any(hmac.compare_digest(x_runtime_token, token) for token in tokens):
        raise HTTPException(
            status_code=401,
            detail={
                "access": "DENIED",
                "reason": "Valid x-runtime-token header required.",
            },
        )


def get_actor_role(
    x_actor_role: str | None = Header(default=None),
    x_runtime_token: str | None = Header(default=None),
) -> Role:
    validate_runtime_token(x_runtime_token)

    if runtime_access_required() and not x_actor_role:
        raise HTTPException(
            status_code=401,
            detail={
                "access": "DENIED",
                "reason": "Explicit x-actor-role header required when production runtime-token enforcement is enabled.",
            },
        )

    try:
        return Role((x_actor_role or "operator").lower())
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid actor role")


def require_role(role: Role, allowed: set[Role]):
    if role not in allowed:
        raise HTTPException(
            status_code=403,
            detail={
                "access": "DENIED",
                "role": role.value,
                "allowed_roles": sorted([r.value for r in allowed]),
            },
        )
