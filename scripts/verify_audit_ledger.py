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
from app.db_models import AuditEvent  # noqa: E402
from app.services.audit import verify_audit_ledger  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify tamper-evident audit ledger chains.")
    parser.add_argument("--request-id", help="Verify a single request id. If omitted, verifies all request chains.")
    args = parser.parse_args()

    with SessionLocal() as db:
        query = db.query(AuditEvent)
        if args.request_id:
            query = query.filter(AuditEvent.request_id == args.request_id)
        events = query.order_by(AuditEvent.request_id.asc(), AuditEvent.created_at.asc(), AuditEvent.id.asc()).all()

    grouped: dict[str, list[AuditEvent]] = defaultdict(list)
    for event in events:
        grouped[event.request_id].append(event)

    results = {request_id: verify_audit_ledger(chain) for request_id, chain in sorted(grouped.items())}
    valid = all(result["valid"] for result in results.values())
    print(json.dumps({"valid": valid, "request_count": len(results), "requests": results}, indent=2, sort_keys=True))
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
