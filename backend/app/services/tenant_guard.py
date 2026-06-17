import os
from fastapi import Header, HTTPException
from sqlalchemy.orm import Session
from app.db_models import OperationRequest, Workflow


def _enabled(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def tenant_header_required() -> bool:
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    return app_env in {"production", "prod"} or _enabled(os.getenv("REQUIRE_TENANT_HEADER"))


def get_tenant_id(x_tenant_id: str | None = Header(default=None)) -> str | None:
    if tenant_header_required() and not x_tenant_id:
        raise HTTPException(
            status_code=401,
            detail={
                "access": "DENIED",
                "reason": "Explicit x-tenant-id header required when tenant enforcement is enabled.",
            },
        )
    return x_tenant_id


def require_tenant_access(resource_customer_id: str, tenant_id: str | None):
    if tenant_id is None:
        return

    if resource_customer_id != tenant_id:
        raise HTTPException(
            status_code=403,
            detail={
                "access": "DENIED",
                "reason": "Tenant boundary violation",
                "tenant_id": tenant_id,
            },
        )


def get_request_for_tenant(db: Session, request_id: str, tenant_id: str | None) -> OperationRequest:
    operation = db.get(OperationRequest, request_id)
    if not operation:
        raise HTTPException(status_code=404, detail="Request not found")

    require_tenant_access(operation.customer_id, tenant_id)
    return operation


def get_workflow_for_tenant(db: Session, workflow_id: str, tenant_id: str | None) -> Workflow:
    workflow = db.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    require_tenant_access(workflow.customer_id, tenant_id)
    return workflow
