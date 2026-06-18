from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.db_models import AuditEvent
from app.services.audit import verify_audit_ledger
from app.services.rbac import Actor, get_actor, require_permission
from app.services.tenant_guard import get_request_for_tenant, get_tenant_id

router = APIRouter()


@router.get("/requests/{request_id}/audit/verify")
def verify_request_audit_ledger(
    request_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
    tenant_id: str | None = Depends(get_tenant_id),
):
    require_permission(actor, "audit:read")
    get_request_for_tenant(db, request_id, tenant_id)
    events = db.query(AuditEvent).filter(AuditEvent.request_id == request_id).order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc()).all()
    return {
        "request_id": request_id,
        "audit_ledger": verify_audit_ledger(events),
    }
