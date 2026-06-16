from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.db_models import OperationRequest, Decision, EvidenceItem, Workflow
from app.models import CustomerRequest, RuntimeDecision
from app.schemas import RequestCreate, EvidenceCreate, ReviewAction, OperationsDashboard, RequestSummary
from app.services.policy_gate import evaluate_request
from app.services.receipt import build_receipt
from app.services.audit import record_event

router = APIRouter()


@router.post("/requests/evaluate", response_model=RuntimeDecision)
def create_and_evaluate_request(payload: RequestCreate, db: Session = Depends(get_db)):
    workflow = db.get(Workflow, payload.workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    existing = db.get(OperationRequest, payload.request_id)
    if existing:
        raise HTTPException(status_code=409, detail="Request already exists")

    req_model = CustomerRequest(**payload.model_dump())
    outcome, effect_status, no_bind, reason_codes = evaluate_request(req_model)
    receipt = build_receipt(req_model, outcome, effect_status, no_bind, reason_codes)

    lifecycle_status = {
        "ADMIT": "ready_to_execute",
        "HOLD": "waiting_for_review",
        "ESCALATE": "pending_approval",
        "REFUSE": "closed_not_released",
    }[outcome.value]

    operation = OperationRequest(
        id=payload.request_id,
        customer_id=payload.customer_id,
        workflow_id=payload.workflow_id,
        requested_action=payload.requested_action,
        business_context=payload.business_context,
        authority_present=payload.authority_present,
        scope_matched=payload.scope_matched,
        evidence_present=payload.evidence_present,
        evidence_fresh=payload.evidence_fresh,
        risk_level=payload.risk_level,
        approval_required=payload.approval_required,
        lifecycle_status=lifecycle_status,
        request_metadata=payload.metadata,
    )
    decision = Decision(
        id=f"decision-{payload.request_id}",
        request_id=payload.request_id,
        outcome=outcome.value,
        protected_effect_status=effect_status,
        no_bind_status=no_bind,
        reason_codes=reason_codes,
        receipt_id=receipt.receipt_id,
        replay_token=receipt.replay_token,
    )

    db.add(operation)
    db.add(decision)
    db.commit()
    record_event(db, payload.request_id, "request_evaluated", detail={"outcome": outcome.value, "status": lifecycle_status})

    return RuntimeDecision(
        request_id=payload.request_id,
        workflow_id=payload.workflow_id,
        outcome=outcome,
        protected_effect_status=effect_status,
        no_bind_status=no_bind,
        reason_codes=reason_codes,
        receipt_id=receipt.receipt_id,
        replay_token=receipt.replay_token,
        customer_visible_summary=f"Request {payload.request_id} produced {outcome.value}. Current status: {lifecycle_status}.",
    )


@router.get("/requests")
def list_requests(db: Session = Depends(get_db)):
    return db.query(OperationRequest).order_by(OperationRequest.created_at.desc()).all()


@router.post("/evidence")
def attach_evidence(payload: EvidenceCreate, db: Session = Depends(get_db)):
    req = db.get(OperationRequest, payload.request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    evidence = EvidenceItem(
        id=payload.id,
        request_id=payload.request_id,
        label=payload.label,
        source=payload.source,
        freshness_status=payload.freshness_status,
        payload=payload.payload,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    record_event(db, payload.request_id, "evidence_attached", detail={"evidence_id": payload.id, "label": payload.label})
    return evidence


@router.post("/requests/{request_id}/review")
def review_request(request_id: str, payload: ReviewAction, db: Session = Depends(get_db)):
    req = db.get(OperationRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    next_status = {
        "approve": "approved_for_execution",
        "hold": "waiting_for_review",
        "escalate": "pending_higher_authority",
        "refuse": "closed_not_released",
    }[payload.decision]

    req.lifecycle_status = next_status
    db.commit()
    record_event(db, request_id, "review_action", actor=payload.actor, detail={"decision": payload.decision, "notes": payload.notes})
    return {"request_id": request_id, "lifecycle_status": next_status}


@router.get("/dashboard", response_model=OperationsDashboard)
def dashboard(db: Session = Depends(get_db)):
    requests = db.query(OperationRequest).order_by(OperationRequest.created_at.desc()).all()
    decisions = db.query(Decision).all()
    outcomes = [d.outcome for d in decisions]
    pending = [r for r in requests if r.lifecycle_status in {"waiting_for_review", "pending_approval", "pending_higher_authority"}]
    recent = [
        RequestSummary(
            request_id=r.id,
            workflow_id=r.workflow_id,
            customer_id=r.customer_id,
            requested_action=r.requested_action,
            lifecycle_status=r.lifecycle_status,
            risk_level=r.risk_level,
            approval_required=r.approval_required,
        )
        for r in requests[:10]
    ]
    return OperationsDashboard(
        total_requests=len(requests),
        admitted=outcomes.count("ADMIT"),
        held=outcomes.count("HOLD"),
        escalated=outcomes.count("ESCALATE"),
        refused=outcomes.count("REFUSE"),
        pending_review=len(pending),
        recent_requests=recent,
    )
