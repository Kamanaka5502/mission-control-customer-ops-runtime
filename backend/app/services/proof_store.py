import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.db_models import AuditEvent, Decision, EvidenceItem, OperationRequest
from app.services.audit import AUDIT_GENESIS_HASH, audit_head_anchor, compute_audit_event_hash, verify_audit_ledger
from app.services.integrity import build_evidence_manifest, build_request_snapshot, stable_hash
from app.services.policy_gate import evaluate_request
from app.services.receipt import SIGNATURE_ALGORITHM, build_receipt, receipt_key_id, sign_public_hash, verify_public_hash_signature, verify_receipt_signature


PROOF_BUNDLE_VERSION = "proof-bundle-v1"
DEFAULT_PROOF_STORE_DIR = "var/proof_store"
SAFE_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]+$")


def proof_store_dir() -> Path:
    return Path(DEFAULT_PROOF_STORE_DIR).resolve()


def safe_request_id(request_id: str) -> str:
    if not SAFE_REQUEST_ID_PATTERN.fullmatch(request_id):
        raise ValueError("request_id contains unsupported characters for proof-store paths")
    return request_id


def proof_bundle_filename(request_id: str) -> str:
    safe_id = safe_request_id(request_id)
    digest = hashlib.sha256(safe_id.encode("utf-8")).hexdigest()
    return f"{digest}.proof.json"


def proof_bundle_path(request_id: str, *, base_dir: Path | None = None) -> Path:
    root = (base_dir or proof_store_dir()).resolve()
    path = (root / proof_bundle_filename(request_id)).resolve()
    if root != path and root not in path.parents:
        raise ValueError("proof bundle path escapes proof-store directory")
    return path


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


def _audit_event_payload(event: AuditEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "request_id": event.request_id,
        "event_type": event.event_type,
        "actor": event.actor,
        "detail": event.detail or {},
        "created_at": event.created_at.replace(microsecond=0).isoformat() if event.created_at else None,
    }


def _compute_proof_hash(proof_body: dict[str, Any]) -> str:
    return stable_hash(proof_body)


def _sign_proof_hash(proof_hash: str) -> str:
    return sign_public_hash(proof_hash)


def _proof_hash_body(bundle: dict[str, Any]) -> dict[str, Any]:
    body = dict(bundle)
    body.pop("proof_hash", None)
    body.pop("proof_hash_algorithm", None)
    body.pop("proof_signature_algorithm", None)
    body.pop("proof_signature_key_id", None)
    body.pop("proof_signature", None)
    return body


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
    original_receipt = build_receipt(
        req_model,
        decision.outcome,
        decision.protected_effect_status,
        decision.no_bind_status,
        decision.reason_codes,
    )
    receipt_payload = original_receipt.model_dump(mode="json")

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
        "audit_anchor": anchor,
        "audit_events": [_audit_event_payload(event) for event in audit_events],
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
    proof_hash = _compute_proof_hash(proof_body)
    return {
        **proof_body,
        "proof_hash_algorithm": "sha256",
        "proof_hash": proof_hash,
        "proof_signature_algorithm": SIGNATURE_ALGORITHM,
        "proof_signature_key_id": receipt_key_id(),
        "proof_signature": _sign_proof_hash(proof_hash),
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


def _verify_snapshot_hash(bundle: dict[str, Any]) -> bool:
    snapshot_container = bundle.get("request_snapshot") or {}
    snapshot = snapshot_container.get("snapshot") or {}
    return snapshot_container.get("snapshot_hash") == stable_hash(snapshot)


def _verify_manifest_hash(bundle: dict[str, Any]) -> bool:
    manifest_container = bundle.get("evidence_manifest") or {}
    manifest = manifest_container.get("manifest") or {}
    return manifest_container.get("manifest_hash") == stable_hash(manifest)


def _verify_audit_events(bundle: dict[str, Any]) -> dict[str, Any]:
    previous_hash = AUDIT_GENESIS_HASH
    failures: list[dict[str, Any]] = []
    events = bundle.get("audit_events") or []
    for index, event in enumerate(events):
        detail = event.get("detail") or {}
        ledger = detail.get("audit_ledger") or {}
        stored_previous = ledger.get("previous_hash")
        stored_hash = ledger.get("event_hash")
        expected_hash = compute_audit_event_hash(
            event_id=str(event.get("id") or ""),
            request_id=str(event.get("request_id") or ""),
            event_type=str(event.get("event_type") or ""),
            actor=str(event.get("actor") or ""),
            detail=detail,
            previous_hash=previous_hash,
        )
        if stored_previous != previous_hash or stored_hash != expected_hash:
            failures.append(
                {
                    "index": index,
                    "event_id": event.get("id"),
                    "expected_previous_hash": previous_hash,
                    "stored_previous_hash": stored_previous,
                    "expected_event_hash": expected_hash,
                    "stored_event_hash": stored_hash,
                }
            )
        previous_hash = str(stored_hash or expected_hash)

    anchor = bundle.get("audit_anchor") or {}
    expected_count = anchor.get("event_count")
    expected_head = anchor.get("head_hash")
    if expected_count is not None and expected_count != len(events):
        failures.append({"reason": "event_count_mismatch", "expected_event_count": expected_count, "observed_event_count": len(events)})
    if expected_head is not None and expected_head != previous_hash:
        failures.append({"reason": "head_hash_mismatch", "expected_head_hash": expected_head, "observed_head_hash": previous_hash})

    return {
        "valid": not failures,
        "event_count": len(events),
        "head_hash": previous_hash,
        "expected_event_count": expected_count,
        "expected_head_hash": expected_head,
        "failures": failures,
    }


def verify_proof_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    provided_hash = bundle.get("proof_hash")
    body = _proof_hash_body(bundle)
    expected_hash = _compute_proof_hash(body)
    provided_signature = str(bundle.get("proof_signature") or "")
    proof_key_id = str(bundle.get("proof_signature_key_id") or "")
    proof_signature_result = verify_public_hash_signature(expected_hash, provided_signature, proof_key_id)

    receipt_result = verify_receipt_signature(bundle.get("receipt") or {})
    audit_result = _verify_audit_events(bundle)
    integrity = bundle.get("integrity") or {}
    replay = bundle.get("replay_result") or {}
    decision = bundle.get("decision") or {}
    receipt = bundle.get("receipt") or {}

    checks = {
        "proof_hash_matches": provided_hash == expected_hash,
        "proof_signature_valid": bool(proof_signature_result.get("valid")),
        "receipt_valid": bool(receipt_result.get("valid")),
        "receipt_preserves_decision_token": decision.get("replay_token") == receipt.get("replay_token"),
        "receipt_preserves_decision_id": decision.get("receipt_id") == receipt.get("receipt_id"),
        "request_snapshot_hash_valid": _verify_snapshot_hash(bundle),
        "evidence_manifest_hash_valid": _verify_manifest_hash(bundle),
        "audit_ledger_valid": bool(audit_result.get("valid")),
        "request_snapshot_match": bool(integrity.get("request_snapshot_match")) and integrity.get("current_request_snapshot_hash") == (bundle.get("request_snapshot") or {}).get("snapshot_hash"),
        "evidence_manifest_match": bool(integrity.get("evidence_manifest_match")) and integrity.get("current_evidence_manifest_hash") == (bundle.get("evidence_manifest") or {}).get("manifest_hash"),
        "same_condition_replay_matched": bool(replay.get("matched")),
    }
    return {
        "valid": all(checks.values()),
        "checks": checks,
        "expected_proof_hash": expected_hash,
        "provided_proof_hash": provided_hash,
        "proof_signature_algorithm": bundle.get("proof_signature_algorithm"),
        "proof_signature_key_id": bundle.get("proof_signature_key_id"),
        "proof_signature_verification": proof_signature_result,
        "receipt_verification": receipt_result,
        "audit_verification": audit_result,
    }
