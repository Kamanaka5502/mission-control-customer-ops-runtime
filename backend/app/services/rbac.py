import os
from enum import Enum
from fastapi import Header, HTTPException


class Role(str, Enum):
    ADMIN = "admin"
    REVIEWER = "reviewer"
    OPERATOR = "operator"
    AUDITOR = "auditor"


def production_mode() -> bool:
    return os.getenv("APP_ENV", "development").strip().lower() in {"production", "prod"}


def get_actor_role(x_actor_role: str | None = Header(default=None)) -> Role:
    if production_mode() and not x_actor_role:
        raise HTTPException(
            status_code=401,
            detail={"access": "DENIED", "reason": "Explicit x-actor-role header required in production mode."},
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
