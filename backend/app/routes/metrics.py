from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.db_models import OperationRequest, Decision, AuditEvent, EvidenceItem

router = APIRouter()


@router.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    requests = db.query(OperationRequest).all()
    decisions = db.query(Decision).all()
    outcomes = [d.outcome for d in decisions]
    statuses = {}
    for req in requests:
        statuses[req.lifecycle_status] = statuses.get(req.lifecycle_status, 0) + 1

    return {
        "service": "mission-control-customer-ops-runtime",
        "total_requests": len(requests),
        "total_decisions": len(decisions),
        "total_evidence_items": db.query(EvidenceItem).count(),
        "total_audit_events": db.query(AuditEvent).count(),
        "outcomes": {
            "ADMIT": outcomes.count("ADMIT"),
            "HOLD": outcomes.count("HOLD"),
            "ESCALATE": outcomes.count("ESCALATE"),
            "REFUSE": outcomes.count("REFUSE"),
        },
        "lifecycle_statuses": statuses,
    }
