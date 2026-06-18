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

from app.services.key_management import auth_verification_secrets, current_auth_secret, is_safe_secret


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
    return current_auth_secret()


def production_auth_config_valid() -> bool:
    return auth_required() and is_safe_secret(signing_secret())


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
    """Create a signed bearer token for tests, local demos, and service accounts."""

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
    try:
        payload_segment, signature_segment = token.split(".", 1)
    except ValueError:
        raise HTTPException(status_code=401, detail={"access": "DENIED", "reason": "Malformed bearer token"})

    try:
        provided_signature = _b64url_decode(signature_segment)
    except Exception:
        raise HTTPException(status_code=401, detail={"access": "DENIED", "reason": "Malformed bearer token signature"})

    verification_secrets = auth_verification_secrets()
    if not verification_secrets:
        raise HTTPException(status_code=500, detail="Auth token secret is not configured")

    signature_valid = False
    for secret in verification_secrets:
        expected_signature = hmac.new(secret.encode("utf-8"), payload_segment.encode("ascii"), hashlib.sha256).digest()
        if hmac.compare_digest(expected_signature, provided_signature):
            signature_valid = True
            break

    if not signature_valid:
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
    x_actor_role: str | None = Header(default=None),
    x_ingress_verified: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
    x_actor_id: str | None = Header(default=None),
    x_actor_scopes: str | None = Header(default=None),
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


def get_actor_role(
    x_actor_role: str | None = Header(default=None),
    x_ingress_verified: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
    x_actor_id: str | None = Header(default=None),
    x_actor_scopes: str | None = Header(default=None),
) -> Role:
    return get_actor(
        x_actor_role=x_actor_role,
        x_ingress_verified=x_ingress_verified,
        authorization=authorization,
        x_actor_id=x_actor_id,
        x_actor_scopes=x_actor_scopes,
    ).role


def require_role(role: Role, allowed: set[Role]):
    if role not in allowed:
        raise HTTPException(status_code=403, detail={"access": "DENIED", "reason": f"Role {role.value} is not allowed"})


def require_permission(actor: Actor, permission: str):
    if actor.role == Role.ADMIN:
        return

    role_permissions = set(PERMISSIONS_BY_ROLE.get(actor.role, set()))
    if permission in role_permissions:
        return

    if actor.role == Role.SERVICE_ACCOUNT and permission in SERVICE_ACCOUNT_ALLOWED_PERMISSIONS and permission in actor.scopes:
        return

    raise HTTPException(
        status_code=403,
        detail={
            "access": "DENIED",
            "reason": f"Actor role {actor.role.value} lacks permission {permission}",
        },
    )
