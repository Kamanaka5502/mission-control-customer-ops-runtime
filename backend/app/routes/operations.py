from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.db_models import OperationRequest, Decision, EvidenceItem, Workflow, AuditEvent
from app.models import CustomerRequest, RuntimeDecision
from app.schemas import RequestCreate, EvidenceCreate, ReviewAction, OperationsDashboard, RequestSummary
from app.services.policy_gate import evaluate_request
from app.services.receipt import build_receipt
from app.services.audit import record_event

router = APIRouter()


def operation_to_customer_request(operation: OperationRequest) -> CustomerRequest:
    return CustomerRequest(
        customer_id=operation.customer_id,
        workflow_id=operation.workflow_id,
        request_id=operation.id,
        requested_action=operation.requested_action,
        business_context=operation.business_context,
        authority_present=operation.authority_present,
        scope_matched=operation.scope_matched,
        evidence_present=operation.evidence_present,
        evidence_fresh=operation.evidence_fresh,
        risk_level=operation.risk_level,
        approval_required=operation.approval_required,
        metadata=operation.request_metadata or {},
    )


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


@router.get("/requests/{request_id}")
def get_request(request_id: str, db: Session = Depends(get_db)):
    req = db.get(OperationRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    return req


@router.post("/requests/{request_id}/execute")
def execute_request(request_id: str, db: Session = Depends(get_db)):
    operation = db.get(OperationRequest, request_id)
    if not operation:
        raise HTTPException(status_code=404, detail="Request not found")

    decision = db.query(Decision).filter(Decision.request_id == request_id).first()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    allowed_statuses = {"ready_to_execute", "approved_for_execution"}
    if operation.lifecycle_status not in allowed_statuses:
        record_event(db, request_id, "execution_blocked", detail={"status": operation.lifecycle_status, "outcome": decision.outcome})
        raise HTTPException(status_code=409, detail={"execution_status": "BLOCKED", "reason": "Request is not in an executable lifecycle state."})

    if decision.outcome != "ADMIT" and operation.lifecycle_status != "approved_for_execution":
        record_event(db, request_id, "execution_blocked", detail={"status": operation.lifecycle_status, "outcome": decision.outcome})
        raise HTTPException(status_code=409, detail={"execution_status": "BLOCKED", "reason": "Runtime decision is not executable without review approval."})

    operation.lifecycle_status = "executed"
    db.commit()
    record_event(db, request_id, "execution_completed", detail={"requested_action": operation.requested_action})
    return {
        "request_id": request_id,
        "execution_status": "EXECUTED",
        "requested_action": operation.requested_action,
        "lifecycle_status": operation.lifecycle_status,
    }


@router.get("/requests/{request_id}/receipt")
def persisted_receipt(request_id: str, db: Session = Depends(get_db)):
    operation = db.get(OperationRequest, request_id)
    if not operation:
        raise HTTPException(status_code=404, detail="Request not found")
    decision = db.query(Decision).filter(Decision.request_id == request_id).first()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    req_model = operation_to_customer_request(operation)
    receipt = build_receipt(
        req_model,
        decision.outcome,
        decision.protected_effect_status,
        decision.no_bind_status,
        decision.reason_codes,
    )
    record_event(db, request_id, "receipt_viewed", detail={"receipt_id": receipt.receipt_id})
    return receipt


@router.post("/requests/{request_id}/replay/same-condition")
def persisted_same_condition_replay(request_id: str, db: Session = Depends(get_db)):
    operation = db.get(OperationRequest, request_id)
    if not operation:
        raise HTTPException(status_code=404, detail="Request not found")
    prior = db.query(Decision).filter(Decision.request_id == request_id).first()
    if not prior:
        raise HTTPException(status_code=404, detail="Decision not found")

    req_model = operation_to_customer_request(operation)
    outcome, effect_status, no_bind, reason_codes = evaluate_request(req_model)
    record_event(db, request_id, "same_condition_replay", detail={"observed_outcome": outcome.value})
    return {
        "request_id": request_id,
        "replay_type": "same_condition",
        "prior_outcome": prior.outcome,
        "observed_outcome": outcome.value,
        "matched": prior.outcome == outcome.value,
        "protected_effect_status": effect_status,
        "no_bind_status": no_bind,
        "reason_codes": reason_codes,
    }


@router.post("/requests/{request_id}/replay/changed-condition")
def persisted_changed_condition_replay(request_id: str, db: Session = Depends(get_db)):
    operation = db.get(OperationRequest, request_id)
    if not operation:
        raise HTTPException(status_code=404, detail="Request not found")

    changed = operation_to_customer_request(operation)
    changed.authority_present = False
    changed.evidence_fresh = False
    changed.risk_level = "high"
    outcome, effect_status, no_bind, reason_codes = evaluate_request(changed)
    record_event(db, request_id, "changed_condition_replay", detail={"observed_outcome": outcome.value})
    return {
        "request_id": request_id,
        "replay_type": "changed_condition",
        "changed_conditions": ["authority_removed", "evidence_stale", "risk_high"],
        "observed_outcome": outcome.value,
        "protected_effect_status": effect_status,
        "no_bind_status": no_bind,
        "reason_codes": reason_codes,
        "customer_visible_proof": "Changed conditions do not inherit the previous authorization posture.",
    }


@router.get("/requests/{request_id}/audit")
def request_audit_trail(request_id: str, db: Session = Depends(get_db)):
    req = db.get(OperationRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    return db.query(AuditEvent).filter(AuditEvent.request_id == request_id).order_by(AuditEvent.created_at.asc()).all()


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
