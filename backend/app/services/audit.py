from uuid import uuid4
from sqlalchemy.orm import Session
from app.db_models import AuditEvent


def record_event(db: Session, request_id: str, event_type: str, actor: str = "system", detail: dict | None = None) -> AuditEvent:
    event = AuditEvent(
        id=f"audit-{uuid4().hex[:12]}",
        request_id=request_id,
        event_type=event_type,
        actor=actor,
        detail=detail or {},
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
