import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from fastapi import Header, HTTPException


class Role(str, Enum):
    REQUESTER = "requester"
    REVIEWER = "reviewer"
    EXECUTOR = "executor"
    AUDITOR = "auditor"
    ADMIN = "admin"
    SERVICE_ACCOUNT = "service_account"
    TENANT_ADMIN = "tenant_admin"
    # Backward-compatible local-demo role. Production deployments should use the
    # explicit roles above.
    OPERATOR = "operator"


@dataclass(frozen=True)
class Actor:
    actor_id: str
    role: Role
    tenant_id: str | None = None
    scopes: frozenset[str] = frozenset()
    authenticated: bool = False
    auth_type: str = "development-header"


TRUE_VALUES = {"1", "true", "yes", "on"}
DEFAULT_SECRET_VALUES = {"", "change-me", "changeme", "dev-secret", "default", "secret"}

PERMISSIONS_BY_ROLE: dict[Role, set[str]] = {
    Role.REQUESTER: {"request:create", "evidence:attach", "request:read", "dashboard:read"},
    Role.REVIEWER: {"request:read", "review:write", "receipt:read", "replay:run", "audit:read", "dashboard:read"},
    Role.EXECUTOR: {"request:read", "execution:run", "execution_job:write", "execution_job:read", "dashboard:read"},
    Role.AUDITOR: {"request:read", "receipt:read", "replay:run", "audit:read", "dashboard:read", "execution_job:read"},
    Role.ADMIN: {"*"},
    Role.TENANT_ADMIN: {"customer:write", "workflow:write", "request:read", "audit:read", "dashboard:read"},
    Role.SERVICE_ACCOUNT: set(),
    # Legacy demo role keeps existing local tests and examples working.
    Role.OPERATOR: {"customer:write", "workflow:write", "request:create", "evidence:attach", "request:read", "execution:run", "execution_job:write", "execution_job:read", "receipt:read", "replay:run", "audit:read", "dashboard:read"},
}

SERVICE_ACCOUNT_ALLOWED_PERMISSIONS = {
    "request:create",
    "evidence:attach",
    "request:read",
    "receipt:read",
    "replay:run",
    "audit:read",
    "dashboard:read",
    "execution_job:read",
    "execution_job:write",
}


def production_mode() -> bool:
    return os.getenv("APP_ENV", "development").strip().lower() in {"production", "prod"}


def _enabled(value: str | None) -> bool:
    return (value or "").strip().lower() in TRUE_VALUES


def auth_required() -> bool:
    return production_mode() or _enabled(os.getenv("AUTH_REQUIRED"))


def trusted_ingress_required() -> bool:
    return production_mode() or _enabled(os.getenv("REQUIRE_TRUSTED_INGRESS"))


def signing_secret() -> str:
    return os.getenv("AUTH_TOKEN_SECRET", "")


def production_auth_config_valid() -> bool:
    secret = signing_secret().strip()
    return auth_required() and secret.lower() not in DEFAULT_SECRET_VALUES and len(secret) >= 32


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def _canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def create_auth_token(
    *,
    actor_id: str,
    role: Role | str,
    tenant_id: str | None = None,
    scopes: list[str] | None = None,
    expires_at: int | None = None,
    secret: str | None = None,
) -> str:
    """Create a signed bearer token for tests, local demos, and service accounts.

    This is intentionally compact: payload JSON plus HMAC-SHA256 signature. It
    avoids trusting app memory and lets tests verify protected-route behavior
    without a full external identity provider.
    """

    key = (secret if secret is not None else signing_secret()).encode("utf-8")
    if not key:
        raise ValueError("AUTH_TOKEN_SECRET is required to create auth tokens")

    role_value = role.value if isinstance(role, Role) else str(role)
    payload: dict[str, Any] = {"sub": actor_id, "role": role_value}
    if tenant_id:
        payload["tenant_id"] = tenant_id
    if scopes:
        payload["scopes"] = sorted(set(scopes))
    if expires_at is not None:
        payload["exp"] = expires_at

    payload_segment = _b64url_encode(_canonical_json(payload))
    signature = hmac.new(key, payload_segment.encode("ascii"), hashlib.sha256).digest()
    return f"{payload_segment}.{_b64url_encode(signature)}"


def verify_auth_token(token: str) -> Actor:
    key = signing_secret().encode("utf-8")
    if not key:
        raise HTTPException(status_code=500, detail="Auth token secret is not configured")

    try:
        payload_segment, signature_segment = token.split(".", 1)
    except ValueError:
        raise HTTPException(status_code=401, detail={"access": "DENIED", "reason": "Malformed bearer token"})

    expected_signature = hmac.new(key, payload_segment.encode("ascii"), hashlib.sha256).digest()
    try:
        provided_signature = _b64url_decode(signature_segment)
    except Exception:
        raise HTTPException(status_code=401, detail={"access": "DENIED", "reason": "Malformed bearer token signature"})

    if not hmac.compare_digest(expected_signature, provided_signature):
        raise HTTPException(status_code=401, detail={"access": "DENIED", "reason": "Invalid bearer token signature"})

    try:
        payload = json.loads(_b64url_decode(payload_segment))
    except Exception:
        raise HTTPException(status_code=401, detail={"access": "DENIED", "reason": "Malformed bearer token payload"})

    exp = payload.get("exp")
    if exp is not None and int(exp) < int(time.time()):
        raise HTTPException(status_code=401, detail={"access": "DENIED", "reason": "Bearer token expired"})

    try:
        role = Role(str(payload["role"]).lower())
    except (KeyError, ValueError):
        raise HTTPException(status_code=403, detail={"access": "DENIED", "reason": "Invalid bearer token role"})

    actor_id = str(payload.get("sub") or "").strip()
    if not actor_id:
        raise HTTPException(status_code=401, detail={"access": "DENIED", "reason": "Bearer token subject required"})

    scopes = payload.get("scopes") or []
    if not isinstance(scopes, list):
        raise HTTPException(status_code=401, detail={"access": "DENIED", "reason": "Bearer token scopes must be a list"})

    return Actor(
        actor_id=actor_id,
        role=role,
        tenant_id=payload.get("tenant_id"),
        scopes=frozenset(str(scope) for scope in scopes),
        authenticated=True,
        auth_type="bearer",
    )


def require_trusted_ingress(x_ingress_verified: str | None):
    if not trusted_ingress_required():
        return

    if not _enabled(x_ingress_verified):
        raise HTTPException(
            status_code=401,
            detail={
                "access": "DENIED",
                "reason": "Trusted ingress verification required in production mode.",
            },
        )


def get_actor(
    authorization: str | None = Header(default=None),
    x_actor_role: str | None = Header(default=None),
    x_actor_id: str | None = Header(default=None),
    x_actor_scopes: str | None = Header(default=None),
    x_ingress_verified: str | None = Header(default=None),
) -> Actor:
    require_trusted_ingress(x_ingress_verified)

    if auth_required():
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail={"access": "DENIED", "reason": "Bearer token required"})
        return verify_auth_token(authorization.split(" ", 1)[1].strip())

    if production_mode() and not x_actor_role:
        raise HTTPException(
            status_code=401,
            detail={"access": "DENIED", "reason": "Explicit x-actor-role header required in production mode."},
        )

    try:
        role = Role((x_actor_role or "operator").lower())
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid actor role")

    scopes = frozenset(
        scope.strip()
        for scope in (x_actor_scopes or "").split(",")
        if scope.strip()
    )
    return Actor(
        actor_id=x_actor_id or role.value,
        role=role,
        scopes=scopes,
        authenticated=False,
        auth_type="development-header",
    )


def get_actor_role(actor: Actor = None) -> Role:
    # FastAPI dependency-compatible wrapper. The default None is only for direct
    # calls in tests; route injection should call get_actor_role via Depends.
    if actor is None:
        raise HTTPException(status_code=500, detail="Actor dependency not resolved")
    return actor.role


def get_actor_role_dependency(
    actor: Actor = Header(default=None),
):
    return actor.role


def role_from_actor(actor: Actor) -> Role:
    return actor.role


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


def require_permission(actor: Actor, permission: str):
    if actor.role == Role.SERVICE_ACCOUNT:
        if permission not in SERVICE_ACCOUNT_ALLOWED_PERMISSIONS:
            raise HTTPException(
                status_code=403,
                detail={"access": "DENIED", "role": actor.role.value, "reason": "Service account endpoint not allowed"},
            )
        if permission not in actor.scopes and "*" not in actor.scopes:
            raise HTTPException(
                status_code=403,
                detail={"access": "DENIED", "role": actor.role.value, "missing_scope": permission},
            )
        return

    permissions = PERMISSIONS_BY_ROLE.get(actor.role, set())
    if "*" in permissions or permission in permissions:
        return

    raise HTTPException(
        status_code=403,
        detail={"access": "DENIED", "role": actor.role.value, "required_permission": permission},
    )
