import hashlib
import json
from datetime import datetime
from typing import Any

from app.db_models import EvidenceItem, OperationRequest


INTEGRITY_HASH_ALGORITHM = "sha256"
REQUEST_SNAPSHOT_VERSION = "request-snapshot-v1"
EVIDENCE_MANIFEST_VERSION = "evidence-manifest-v1"


def _normalize(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat()
    if isinstance(value, dict):
        return {str(k): _normalize(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    return value


def stable_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(_normalize(payload), sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_request_snapshot(operation: OperationRequest) -> dict[str, Any]:
    snapshot = {
        "snapshot_version": REQUEST_SNAPSHOT_VERSION,
        "request_id": operation.id,
        "customer_id": operation.customer_id,
        "workflow_id": operation.workflow_id,
        "requested_action": operation.requested_action,
        "business_context": operation.business_context,
        "authority_present": operation.authority_present,
        "scope_matched": operation.scope_matched,
        "evidence_present": operation.evidence_present,
        "evidence_fresh": operation.evidence_fresh,
        "risk_level": operation.risk_level,
        "approval_required": operation.approval_required,
        "metadata": operation.request_metadata or {},
    }
    return {
        "hash_algorithm": INTEGRITY_HASH_ALGORITHM,
        "snapshot_hash": stable_hash(snapshot),
        "snapshot": snapshot,
    }


def build_evidence_manifest(evidence_items: list[EvidenceItem]) -> dict[str, Any]:
    items = []
    for evidence in sorted(evidence_items, key=lambda item: item.id):
        payload = evidence.payload or {}
        items.append(
            {
                "id": evidence.id,
                "request_id": evidence.request_id,
                "label": evidence.label,
                "source": evidence.source,
                "freshness_status": evidence.freshness_status,
                "payload_hash": stable_hash(payload),
                "payload_redacted": True,
            }
        )

    manifest = {
        "manifest_version": EVIDENCE_MANIFEST_VERSION,
        "evidence_count": len(items),
        "items": items,
    }
    return {
        "hash_algorithm": INTEGRITY_HASH_ALGORITHM,
        "manifest_hash": stable_hash(manifest),
        "manifest": manifest,
    }
