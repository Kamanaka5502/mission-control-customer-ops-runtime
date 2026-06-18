from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.db_models import AuditEvent, Decision, EvidenceItem, OperationRequest
from app.models import CustomerRequest, RuntimeDecision
from app.schemas import EvidenceCreate, OperationsDashboard, RequestCreate, RequestSummary, ReviewAction
from app.services.audit import record_event
from app.services.integrity import build_evidence_manifest, build_request_snapshot
from app.services.policy_gate import evaluate_request
from app.services.rbac import Actor, get_actor, require_permission
from app.services.receipt import build_receipt
from app.services.tenant_guard import get_request_for_tenant, get_tenant_id, get_workflow_for_tenant, require_tenant_access

router = APIRouter()

EXECUTION_CONTROL_KEY = "execution_control"


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


def actor_name(actor: Actor) -> str:
    return actor.actor_id or actor.role.value


def _latest_integrity_event(events: list[AuditEvent], event_type: str) -> AuditEvent | None:
    matching = [event for event in events if event.event_type == event_type]
    return matching[-1] if matching else None


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _stored_execution_result(operation: OperationRequest) -> dict | None:
    control = (operation.request_metadata or {}).get(EXECUTION_CONTROL_KEY)
    if not isinstance(control, dict):
        return None
    result = control.get("result")
    return result if isinstance(result, dict) else None


def _store_execution_result(operation: OperationRequest, result: dict) -> None:
    metadata = dict(operation.request_metadata or {})
    metadata[EXECUTION_CONTROL_KEY] = {
        "result": {**result, "idempotent_replay": False},
        "completed_at": _utc_now(),
    }
    operation.request_metadata = metadata


def _execution_result(operation: OperationRequest, decision: Decision, *, idempotent_replay: bool) -> dict:
    return {
        "request_id": operation.id,
        "execution_status": "EXECUTED",
        "requested_action": operation.requested_action,
        "lifecycle_status": "executed",
        "decision_outcome": decision.outcome,
        "receipt_id": decision.receipt_id,
        "idempotent_replay": idempotent_replay,
    }


def _final_execution_error(operation: OperationRequest, decision: Decision) -> str | None:
    if decision.outcome == "REFUSE":
        return "Closed request is not releasable."

    allowed_statuses = {"ready_to_execute", "approved_for_execution"}
    if operation.lifecycle_status not in allowed_statuses:
        return "Request is not in an executable lifecycle state."

    if decision.outcome == "HOLD":
        return "Held request is not executable."

    if decision.outcome in {"ESCALATE", "HOLD"} and operation.lifecycle_status != "approved_for_execution":
        return "Request requires approval before execution."

    if decision.outcome != "ADMIT" and operation.lifecycle_status != "approved_for_execution":
        return "Runtime decision is not executable without review approval."

    req_model = operation_to_customer_request(operation)
    current_outcome, current_effect_status, current_no_bind, _ = evaluate_request(req_model)
    if current_outcome.value != decision.outcome:
        return "Current runtime decision no longer matches stored decision."
    if current_effect_status != decision.protected_effect_status:
        return "Current protected-effect status no longer matches stored decision."
    if current_no_bind != decision.no_bind_status:
        return "Current no-bind status no longer matches stored decision."

    return None


@router.post("/requests/evaluate", response_model=RuntimeDecision)
def create_and_evaluate_request(
    payload: RequestCreate,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
    tenant_id: str | None = Depends(get_tenant_id),
):
    require_permission(actor, "request:create")
    require_tenant_access(payload.customer_id, tenant_id)

    get_workflow_for_tenant(db, payload.workflow_id, tenant_id)

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
    db.refresh(operation)

    snapshot = build_request_snapshot(operation)
    record_event(
        db,
        payload.request_id,
        "request_snapshot_captured",
        actor=actor_name(actor),
        detail=snapshot,
    )
    record_event(db, payload.request_id, "request_evaluated", actor=actor_name(actor), detail={"outcome": outcome.value, "status": lifecycle_status})

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
def list_requests(
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
    tenant_id: str | None = Depends(get_tenant_id),
):
    require_permission(actor, "request:read")
    query = db.query(OperationRequest).order_by(OperationRequest.created_at.desc())
    if tenant_id:
        query = query.filter(OperationRequest.customer_id == tenant_id)
    return query.all()


@router.get("/requests/{request_id}")
def get_request(
    request_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
    tenant_id: str | None = Depends(get_tenant_id),
):
    require_permission(actor, "request:read")
    return get_request_for_tenant(db, request_id, tenant_id)


@router.post("/requests/{request_id}/execute")
def execute_request(
    request_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
    tenant_id: str | None = Depends(get_tenant_id),
):
    require_permission(actor, "execution:run")

    operation = get_request_for_tenant(db, request_id, tenant_id)
    decision = db.query(Decision).filter(Decision.request_id == request_id).first()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    stored_result = _stored_execution_result(operation)
    if operation.lifecycle_status == "executed" and stored_result:
        replay_result = {**stored_result, "idempotent_replay": True}
        record_event(db, request_id, "execution_idempotent_replay", actor=actor_name(actor), detail={"receipt_id": decision.receipt_id})
        return replay_result

    if operation.lifecycle_status == "executed":
        replay_result = _execution_result(operation, decision, idempotent_replay=True)
        record_event(db, request_id, "execution_idempotent_replay", actor=actor_name(actor), detail={"receipt_id": decision.receipt_id})
        return replay_result

    final_error = _final_execution_error(operation, decision)
    if final_error:
        record_event(db, request_id, "execution_blocked", actor=actor_name(actor), detail={"status": operation.lifecycle_status, "outcome": decision.outcome, "reason": final_error})
        raise HTTPException(status_code=409, detail={"execution_status": "BLOCKED", "reason": final_error})

    result = _execution_result(operation, decision, idempotent_replay=False)
    operation.lifecycle_status = "executed"
    _store_execution_result(operation, result)
    db.commit()
    record_event(db, request_id, "execution_completed", actor=actor_name(actor), detail={"requested_action": operation.requested_action, "receipt_id": decision.receipt_id})
    return result


@router.get("/requests/{request_id}/receipt")
def persisted_receipt(
    request_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
    tenant_id: str | None = Depends(get_tenant_id),
):
    require_permission(actor, "receipt:read")

    operation = get_request_for_tenant(db, request_id, tenant_id)
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
    record_event(db, request_id, "receipt_viewed", actor=actor_name(actor), detail={"receipt_id": receipt.receipt_id})
    return receipt


@router.post("/requests/{request_id}/replay/same-condition")
def persisted_same_condition_replay(
    request_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
    tenant_id: str | None = Depends(get_tenant_id),
):
    require_permission(actor, "replay:run")

    operation = get_request_for_tenant(db, request_id, tenant_id)
    prior = db.query(Decision).filter(Decision.request_id == request_id).first()
    if not prior:
        raise HTTPException(status_code=404, detail="Decision not found")

    req_model = operation_to_customer_request(operation)
    outcome, effect_status, no_bind, reason_codes = evaluate_request(req_model)
    record_event(db, request_id, "same_condition_replay", actor=actor_name(actor), detail={"observed_outcome": outcome.value})
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
def persisted_changed_condition_replay(
    request_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
    tenant_id: str | None = Depends(get_tenant_id),
):
    require_permission(actor, "replay:run")

    operation = get_request_for_tenant(db, request_id, tenant_id)

    changed = operation_to_customer_request(operation)
    changed.authority_present = False
    changed.evidence_fresh = False
    changed.risk_level = "high"

    outcome, effect_status, no_bind, reason_codes = evaluate_request(changed)
    record_event(db, request_id, "changed_condition_replay", actor=actor_name(actor), detail={"observed_outcome": outcome.value})
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
def request_audit_trail(
    request_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
    tenant_id: str | None = Depends(get_tenant_id),
):
    require_permission(actor, "audit:read")

    get_request_for_tenant(db, request_id, tenant_id)
    return db.query(AuditEvent).filter(AuditEvent.request_id == request_id).order_by(AuditEvent.created_at.asc()).all()


@router.get("/requests/{request_id}/integrity")
def request_integrity_report(
    request_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
    tenant_id: str | None = Depends(get_tenant_id),
):
    require_permission(actor, "audit:read")

    operation = get_request_for_tenant(db, request_id, tenant_id)
    evidence_items = db.query(EvidenceItem).filter(EvidenceItem.request_id == request_id).order_by(EvidenceItem.id.asc()).all()
    events = db.query(AuditEvent).filter(AuditEvent.request_id == request_id).order_by(AuditEvent.created_at.asc()).all()

    current_snapshot = build_request_snapshot(operation)
    current_manifest = build_evidence_manifest(evidence_items)
    captured_snapshot_event = _latest_integrity_event(events, "request_snapshot_captured")
    captured_manifest_event = _latest_integrity_event(events, "evidence_manifest_captured")

    captured_snapshot_hash = None
    if captured_snapshot_event:
        captured_snapshot_hash = (captured_snapshot_event.detail or {}).get("snapshot_hash")

    captured_manifest_hash = None
    if captured_manifest_event:
        captured_manifest_hash = (captured_manifest_event.detail or {}).get("manifest_hash")

    return {
        "request_id": request_id,
        "request_snapshot": {
            "captured_hash": captured_snapshot_hash,
            "current_hash": current_snapshot["snapshot_hash"],
            "match": captured_snapshot_hash == current_snapshot["snapshot_hash"],
            "captured": captured_snapshot_hash is not None,
        },
        "evidence_manifest": {
            "captured_hash": captured_manifest_hash,
            "current_hash": current_manifest["manifest_hash"],
            "match": captured_manifest_hash == current_manifest["manifest_hash"] if captured_manifest_hash else current_manifest["manifest"]["evidence_count"] == 0,
            "captured": captured_manifest_hash is not None,
            "evidence_count": current_manifest["manifest"]["evidence_count"],
        },
        "integrity_status": "VERIFIED" if captured_snapshot_hash == current_snapshot["snapshot_hash"] and (captured_manifest_hash == current_manifest["manifest_hash"] if captured_manifest_hash else current_manifest["manifest"]["evidence_count"] == 0) else "REVIEW_REQUIRED",
    }


@router.post("/evidence")
def attach_evidence(
    payload: EvidenceCreate,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
    tenant_id: str | None = Depends(get_tenant_id),
):
    require_permission(actor, "evidence:attach")

    get_request_for_tenant(db, payload.request_id, tenant_id)

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

    evidence_items = db.query(EvidenceItem).filter(EvidenceItem.request_id == payload.request_id).order_by(EvidenceItem.id.asc()).all()
    manifest = build_evidence_manifest(evidence_items)
    record_event(db, payload.request_id, "evidence_attached", actor=actor_name(actor), detail={"evidence_id": payload.id, "label": payload.label})
    record_event(db, payload.request_id, "evidence_manifest_captured", actor=actor_name(actor), detail=manifest)
    return evidence


@router.post("/requests/{request_id}/review")
def review_request(
    request_id: str,
    payload: ReviewAction,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
    tenant_id: str | None = Depends(get_tenant_id),
):
    require_permission(actor, "review:write")

    req = get_request_for_tenant(db, request_id, tenant_id)
    decision = db.query(Decision).filter(Decision.request_id == request_id).first()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    if payload.decision == "approve" and decision.outcome == "REFUSE":
        record_event(db, request_id, "review_blocked", actor=payload.actor or actor_name(actor), detail={"decision": payload.decision, "outcome": decision.outcome})
        raise HTTPException(status_code=409, detail={"review_status": "BLOCKED", "reason": "Closed request is not approvable."})

    next_status = {
        "approve": "approved_for_execution",
        "hold": "waiting_for_review",
        "escalate": "pending_higher_authority",
        "refuse": "closed_not_released",
    }[payload.decision]

    req.lifecycle_status = next_status
    db.commit()
    record_event(db, request_id, "review_action", actor=payload.actor or actor_name(actor), detail={"decision": payload.decision, "notes": payload.notes})
    return {"request_id": request_id, "lifecycle_status": next_status}


@router.get("/dashboard", response_model=OperationsDashboard)
def dashboard(
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
    tenant_id: str | None = Depends(get_tenant_id),
):
    require_permission(actor, "dashboard:read")

    requests_query = db.query(OperationRequest).order_by(OperationRequest.created_at.desc())
    decisions_query = db.query(Decision).join(OperationRequest, Decision.request_id == OperationRequest.id)

    if tenant_id:
        requests_query = requests_query.filter(OperationRequest.customer_id == tenant_id)
        decisions_query = decisions_query.filter(OperationRequest.customer_id == tenant_id)

    requests = requests_query.all()
    decisions = decisions_query.all()
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
