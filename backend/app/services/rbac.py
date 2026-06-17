from enum import Enum
from fastapi import Header, HTTPException


class Role(str, Enum):
    ADMIN = "admin"
    REVIEWER = "reviewer"
    OPERATOR = "operator"
    AUDITOR = "auditor"


def get_actor_role(x_actor_role: str | None = Header(default="operator")) -> Role:
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
