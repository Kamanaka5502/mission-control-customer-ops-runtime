#!/usr/bin/env python3
"""Verify Mission Control audit ledger chains from the configured database."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.database import SessionLocal  # noqa: E402
from app.db_models import AuditEvent, OperationRequest  # noqa: E402
from app.services.audit import audit_head_anchor, verify_audit_ledger  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify tamper-evident audit ledger chains.")
    parser.add_argument("--request-id", help="Verify a single request id. If omitted, verifies all request chains.")
    args = parser.parse_args()

    with SessionLocal() as db:
        query = db.query(AuditEvent)
        operations_query = db.query(OperationRequest)
        if args.request_id:
            query = query.filter(AuditEvent.request_id == args.request_id)
            operations_query = operations_query.filter(OperationRequest.id == args.request_id)
        events = query.order_by(AuditEvent.request_id.asc(), AuditEvent.created_at.asc(), AuditEvent.id.asc()).all()
        operations = {operation.id: operation for operation in operations_query.all()}

    grouped: dict[str, list[AuditEvent]] = defaultdict(list)
    for event in events:
        grouped[event.request_id].append(event)

    results = {}
    for request_id, chain in sorted(grouped.items()):
        anchor = audit_head_anchor(operations.get(request_id)) or {}
        results[request_id] = verify_audit_ledger(
            chain,
            expected_head_hash=anchor.get("head_hash"),
            expected_event_count=anchor.get("event_count"),
        )

    valid = all(result["valid"] for result in results.values())
    print(json.dumps({"valid": valid, "request_count": len(results), "requests": results}, indent=2, sort_keys=True))
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
