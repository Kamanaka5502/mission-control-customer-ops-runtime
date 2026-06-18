from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.db_models import AuditEvent, Decision, EvidenceItem, OperationRequest

router = APIRouter()

SERVICE_NAME = "mission-control-customer-ops-runtime"
EXPECTED_SCHEMA_HEAD = "20260617_0001"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def database_probe() -> dict[str, Any]:
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return {"status": "available"}
    except Exception as exc:
        return {"status": "unavailable", "error_type": type(exc).__name__}
    finally:
        db.close()


def schema_probe() -> dict[str, Any]:
    db = SessionLocal()
    try:
        current = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
    except Exception as exc:
        return {
            "status": "unmanaged",
            "schema_head": EXPECTED_SCHEMA_HEAD,
            "schema_version": None,
            "up_to_date": False,
            "error_type": type(exc).__name__,
        }
    finally:
        db.close()

    return {
        "status": "managed" if current else "unmanaged",
        "schema_head": EXPECTED_SCHEMA_HEAD,
        "schema_version": current,
        "up_to_date": current == EXPECTED_SCHEMA_HEAD,
    }


def runtime_counts(db: Session) -> dict[str, Any]:
    decisions = db.query(Decision).all()
    outcomes = [decision.outcome for decision in decisions]
    requests = db.query(OperationRequest).all()
    statuses: dict[str, int] = {}
    for request in requests:
        statuses[request.lifecycle_status] = statuses.get(request.lifecycle_status, 0) + 1

    return {
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


def alert_checks(*, db_status: dict[str, Any], schema_status: dict[str, Any], counts: dict[str, Any]) -> list[dict[str, str]]:
    alerts: list[dict[str, str]] = []
    if db_status.get("status") != "available":
        alerts.append({"severity": "critical", "code": "DATABASE_UNAVAILABLE", "message": "Database probe failed."})
    if schema_status.get("status") == "managed" and schema_status.get("up_to_date") is False:
        alerts.append({"severity": "warning", "code": "SCHEMA_VERSION_DRIFT", "message": "Database schema is not at expected head."})
    pending = counts.get("lifecycle_statuses", {}).get("pending_approval", 0) + counts.get("lifecycle_statuses", {}).get("pending_higher_authority", 0)
    if pending:
        alerts.append({"severity": "info", "code": "PENDING_REVIEW", "message": f"{pending} request(s) are waiting for review."})
    if counts.get("outcomes", {}).get("REFUSE", 0):
        alerts.append({"severity": "info", "code": "REFUSAL_EVENTS_PRESENT", "message": "One or more requests reached REFUSE."})
    return alerts


@router.get("/ops/monitoring")
def monitoring_profile(db: Session = Depends(get_db)):
    db_status = database_probe()
    schema_status = schema_probe()
    counts = runtime_counts(db)
    alerts = alert_checks(db_status=db_status, schema_status=schema_status, counts=counts)
    health = "healthy" if db_status.get("status") == "available" else "degraded"

    return {
        "service": SERVICE_NAME,
        "generated_at": _utc_now(),
        "environment": os.getenv("APP_ENV", "development"),
        "health": health,
        "database": db_status,
        "schema": schema_status,
        "runtime_counts": counts,
        "alerts": alerts,
        "incident_handoff": {
            "correlation_id_required": True,
            "first_checks": ["/health", "/ready", "/schema-version", "/ops/monitoring"],
            "evidence_to_capture": ["correlation id", "request id", "timestamp", "actor id", "tenant id", "recent audit events"],
        },
    }
