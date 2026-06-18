import hashlib
import json
import threading
from collections import defaultdict
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.db_models import AuditEvent, OperationRequest


AUDIT_HASH_ALGORITHM = "sha256"
AUDIT_GENESIS_HASH = "GENESIS"
AUDIT_LEDGER_KEY = "audit_ledger"
AUDIT_LEDGER_HEAD_KEY = "audit_ledger_head"

_LOCKS_GUARD = threading.Lock()
_REQUEST_LOCKS: dict[str, threading.RLock] = defaultdict(threading.RLock)


def _request_lock(request_id: str) -> threading.RLock:
    with _LOCKS_GUARD:
        return _REQUEST_LOCKS[request_id]


def _normalize(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat()
    if isinstance(value, dict):
        return {str(k): _normalize(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    return value


def _stable_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(_normalize(payload), sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _detail_without_ledger(detail: dict[str, Any] | None) -> dict[str, Any]:
    cleaned = dict(detail or {})
    cleaned.pop(AUDIT_LEDGER_KEY, None)
    return cleaned


def _latest_event_hash(db: Session, request_id: str) -> str:
    latest = (
        db.query(AuditEvent)
        .filter(AuditEvent.request_id == request_id)
        .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .first()
    )
    if not latest:
        return AUDIT_GENESIS_HASH
    ledger = (latest.detail or {}).get(AUDIT_LEDGER_KEY) or {}
    return str(ledger.get("event_hash") or AUDIT_GENESIS_HASH)


def _update_head_anchor(db: Session, request_id: str, *, event_hash: str, event_count: int) -> None:
    operation = db.get(OperationRequest, request_id)
    if not operation:
        return

    metadata = dict(operation.request_metadata or {})
    metadata[AUDIT_LEDGER_HEAD_KEY] = {
        "hash_algorithm": AUDIT_HASH_ALGORITHM,
        "head_hash": event_hash,
        "event_count": event_count,
    }
    operation.request_metadata = metadata
    flag_modified(operation, "request_metadata")


def audit_head_anchor(operation: OperationRequest | None) -> dict[str, Any] | None:
    if not operation:
        return None
    metadata = operation.request_metadata or {}
    anchor = metadata.get(AUDIT_LEDGER_HEAD_KEY)
    return anchor if isinstance(anchor, dict) else None


def compute_audit_event_hash(*, event_id: str, request_id: str, event_type: str, actor: str, detail: dict[str, Any], previous_hash: str) -> str:
    return _stable_hash(
        {
            "event_id": event_id,
            "request_id": request_id,
            "event_type": event_type,
            "actor": actor,
            "detail": _detail_without_ledger(detail),
            "previous_hash": previous_hash,
        }
    )


def record_event(db: Session, request_id: str, event_type: str, actor: str = "system", detail: dict | None = None) -> AuditEvent:
    with _request_lock(request_id):
        event_id = f"audit-{uuid4().hex[:12]}"
        previous_hash = _latest_event_hash(db, request_id)
        clean_detail = _detail_without_ledger(detail)
        event_hash = compute_audit_event_hash(
            event_id=event_id,
            request_id=request_id,
            event_type=event_type,
            actor=actor,
            detail=clean_detail,
            previous_hash=previous_hash,
        )
        event_detail = {
            **clean_detail,
            AUDIT_LEDGER_KEY: {
                "hash_algorithm": AUDIT_HASH_ALGORITHM,
                "previous_hash": previous_hash,
                "event_hash": event_hash,
            },
        }
        event = AuditEvent(
            id=event_id,
            request_id=request_id,
            event_type=event_type,
            actor=actor,
            detail=event_detail,
        )
        db.add(event)
        db.flush()
        event_count = db.query(AuditEvent).filter(AuditEvent.request_id == request_id).count()
        _update_head_anchor(db, request_id, event_hash=event_hash, event_count=event_count)
        db.commit()
        db.refresh(event)
        return event


def verify_audit_ledger(events: list[AuditEvent], *, expected_head_hash: str | None = None, expected_event_count: int | None = None) -> dict[str, Any]:
    previous_hash = AUDIT_GENESIS_HASH
    failures: list[dict[str, Any]] = []

    for index, event in enumerate(events):
        detail = event.detail or {}
        ledger = detail.get(AUDIT_LEDGER_KEY) or {}
        stored_previous = ledger.get("previous_hash")
        stored_hash = ledger.get("event_hash")
        expected_hash = compute_audit_event_hash(
            event_id=event.id,
            request_id=event.request_id,
            event_type=event.event_type,
            actor=event.actor,
            detail=detail,
            previous_hash=previous_hash,
        )

        if stored_previous != previous_hash or stored_hash != expected_hash:
            failures.append(
                {
                    "index": index,
                    "event_id": event.id,
                    "event_type": event.event_type,
                    "expected_previous_hash": previous_hash,
                    "stored_previous_hash": stored_previous,
                    "expected_event_hash": expected_hash,
                    "stored_event_hash": stored_hash,
                }
            )

        previous_hash = str(stored_hash or expected_hash)

    if expected_event_count is not None and expected_event_count != len(events):
        failures.append(
            {
                "reason": "event_count_mismatch",
                "expected_event_count": expected_event_count,
                "observed_event_count": len(events),
            }
        )

    if expected_head_hash is not None and expected_head_hash != previous_hash:
        failures.append(
            {
                "reason": "head_hash_mismatch",
                "expected_head_hash": expected_head_hash,
                "observed_head_hash": previous_hash,
            }
        )

    return {
        "valid": not failures,
        "event_count": len(events),
        "head_hash": previous_hash,
        "expected_event_count": expected_event_count,
        "expected_head_hash": expected_head_hash,
        "failures": failures,
        "hash_algorithm": AUDIT_HASH_ALGORITHM,
    }
