import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.db_models import AuditEvent, Decision, EvidenceItem, OperationRequest
from app.services.audit import audit_head_anchor, verify_audit_ledger
from app.services.integrity import build_evidence_manifest, build_request_snapshot, stable_hash
from app.services.policy_gate import evaluate_request
from app.services.receipt import build_receipt, verify_receipt_signature


PROOF_BUNDLE_VERSION = "proof-bundle-v1"
DEFAULT_PROOF_STORE_DIR = "var/proof_store"


def proof_store_dir() -> Path:
    return Path(os.getenv("PROOF_STORE_PATH", DEFAULT_PROOF_STORE_DIR))


def proof_bundle_path(request_id: str, *, base_dir: Path | None = None) -> Path:
    root = base_dir or proof_store_dir()
    return root / f"{request_id}.proof.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _operation_to_customer_request(operation: OperationRequest):
    from app.models import CustomerRequest

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


def _latest_event(events: list[AuditEvent], event_type: str) -> AuditEvent | None:
    matching = [event for event in events if event.event_type == event_type]
    return matching[-1] if matching else None


def build_proof_bundle(db: Session, request_id: str) -> dict[str, Any]:
    operation = db.get(OperationRequest, request_id)
    if not operation:
        raise ValueError(f"Request not found: {request_id}")

    decision = db.query(Decision).filter(Decision.request_id == request_id).first()
    if not decision:
        raise ValueError(f"Decision not found: {request_id}")

    evidence_items = db.query(EvidenceItem).filter(EvidenceItem.request_id == request_id).order_by(EvidenceItem.id.asc()).all()
    audit_events = db.query(AuditEvent).filter(AuditEvent.request_id == request_id).order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc()).all()

    request_snapshot = build_request_snapshot(operation)
    evidence_manifest = build_evidence_manifest(evidence_items)
    captured_snapshot_event = _latest_event(audit_events, "request_snapshot_captured")
    captured_manifest_event = _latest_event(audit_events, "evidence_manifest_captured")
    captured_snapshot_hash = (captured_snapshot_event.detail or {}).get("snapshot_hash") if captured_snapshot_event else None
    captured_manifest_hash = (captured_manifest_event.detail or {}).get("manifest_hash") if captured_manifest_event else None

    req_model = _operation_to_customer_request(operation)
    receipt = build_receipt(
        req_model,
        decision.outcome,
        decision.protected_effect_status,
        decision.no_bind_status,
        decision.reason_codes,
        request_snapshot_hash=request_snapshot["snapshot_hash"],
        evidence_manifest_hash=evidence_manifest["manifest_hash"],
    )
    receipt_payload = receipt.model_dump(mode="json")

    replay_outcome, replay_status, replay_no_bind, replay_reason_codes = evaluate_request(req_model)
    replay_result = {
        "replay_type": "same_condition",
        "prior_outcome": decision.outcome,
        "observed_outcome": replay_outcome.value,
        "matched": decision.outcome == replay_outcome.value,
        "protected_effect_status": replay_status,
        "no_bind_status": replay_no_bind,
        "reason_codes": replay_reason_codes,
    }

    anchor = audit_head_anchor(operation) or {}
    audit_ledger = verify_audit_ledger(
        audit_events,
        expected_head_hash=anchor.get("head_hash"),
        expected_event_count=anchor.get("event_count"),
    )

    proof_body = {
        "proof_bundle_version": PROOF_BUNDLE_VERSION,
        "request_id": request_id,
        "workflow_id": operation.workflow_id,
        "customer_id": operation.customer_id,
        "created_at": _utc_now(),
        "request_snapshot": request_snapshot,
        "evidence_manifest": evidence_manifest,
        "decision": {
            "outcome": decision.outcome,
            "protected_effect_status": decision.protected_effect_status,
            "no_bind_status": decision.no_bind_status,
            "reason_codes": decision.reason_codes,
            "receipt_id": decision.receipt_id,
            "replay_token": decision.replay_token,
        },
        "receipt": receipt_payload,
        "receipt_verification": verify_receipt_signature(receipt_payload),
        "replay_result": replay_result,
        "audit_ledger": audit_ledger,
        "integrity": {
            "request_snapshot_match": captured_snapshot_hash == request_snapshot["snapshot_hash"],
            "captured_request_snapshot_hash": captured_snapshot_hash,
            "current_request_snapshot_hash": request_snapshot["snapshot_hash"],
            "evidence_manifest_match": captured_manifest_hash == evidence_manifest["manifest_hash"] if captured_manifest_hash else evidence_manifest["manifest"]["evidence_count"] == 0,
            "captured_evidence_manifest_hash": captured_manifest_hash,
            "current_evidence_manifest_hash": evidence_manifest["manifest_hash"],
        },
    }
    proof_hash = stable_hash(proof_body)
    return {
        **proof_body,
        "proof_hash_algorithm": "sha256",
        "proof_hash": proof_hash,
    }


def persist_proof_bundle(bundle: dict[str, Any], *, base_dir: Path | None = None) -> dict[str, Any]:
    path = proof_bundle_path(bundle["request_id"], base_dir=base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bundle, indent=2, sort_keys=True), encoding="utf-8")
    return {
        "request_id": bundle["request_id"],
        "proof_hash": bundle["proof_hash"],
        "path": str(path),
        "stored": True,
    }


def load_proof_bundle(request_id: str, *, base_dir: Path | None = None) -> dict[str, Any]:
    path = proof_bundle_path(request_id, base_dir=base_dir)
    return json.loads(path.read_text(encoding="utf-8"))


def verify_proof_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    provided_hash = bundle.get("proof_hash")
    body = dict(bundle)
    body.pop("proof_hash", None)
    body.pop("proof_hash_algorithm", None)
    expected_hash = stable_hash(body)

    receipt_result = verify_receipt_signature(bundle.get("receipt") or {})
    audit_result = bundle.get("audit_ledger") or {}
    integrity = bundle.get("integrity") or {}
    replay = bundle.get("replay_result") or {}

    checks = {
        "proof_hash_matches": provided_hash == expected_hash,
        "receipt_valid": bool(receipt_result.get("valid")),
        "audit_ledger_valid": bool(audit_result.get("valid")),
        "request_snapshot_match": bool(integrity.get("request_snapshot_match")),
        "evidence_manifest_match": bool(integrity.get("evidence_manifest_match")),
        "same_condition_replay_matched": bool(replay.get("matched")),
    }
    return {
        "valid": all(checks.values()),
        "checks": checks,
        "expected_proof_hash": expected_hash,
        "provided_proof_hash": provided_hash,
        "receipt_verification": receipt_result,
    }
