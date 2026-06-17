from fastapi import Header, HTTPException
from sqlalchemy.orm import Session
from app.db_models import OperationRequest, Workflow


def get_tenant_id(x_tenant_id: str | None = Header(default=None)) -> str | None:
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
