from uuid import uuid4

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.db_models import AuditEvent
from app.main import app

client = TestClient(app)


def create_request():
    suffix = uuid4().hex[:8]
    customer_id = f"audit-customer-{suffix}"
    workflow_id = f"audit-workflow-{suffix}"
    request_id = f"REQ-AUDIT-{suffix}"

    customer = client.post(
        "/ops/customers",
        json={"id": customer_id, "name": "Audit Customer", "industry": "operations"},
    )
    assert customer.status_code in {200, 201}

    workflow = client.post(
        "/ops/workflows",
        json={"id": workflow_id, "customer_id": customer_id, "name": "Audit Workflow", "description": "Audit workflow"},
    )
    assert workflow.status_code in {200, 201}

    evaluated = client.post(
        "/ops/requests/evaluate",
        json={
            "customer_id": customer_id,
            "workflow_id": workflow_id,
            "request_id": request_id,
            "requested_action": "approve_audit_action",
            "business_context": "Audit ledger test request",
            "authority_present": True,
            "scope_matched": True,
            "evidence_present": True,
            "evidence_fresh": True,
            "risk_level": "low",
            "approval_required": False,
            "metadata": {"purpose": "audit-ledger-test"},
        },
    )
    assert evaluated.status_code == 200
    return request_id


def test_audit_ledger_verifies_clean_chain():
    request_id = create_request()

    response = client.get(f"/ops/requests/{request_id}/audit/verify")

    assert response.status_code == 200
    body = response.json()
    assert body["audit_ledger"]["valid"] is True
    assert body["audit_ledger"]["event_count"] >= 2
    assert body["audit_ledger"]["failures"] == []


def test_audit_ledger_detects_edit():
    request_id = create_request()

    with SessionLocal() as db:
        event = db.query(AuditEvent).filter(AuditEvent.request_id == request_id).order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc()).first()
        assert event is not None
        edited_detail = dict(event.detail or {})
        edited_detail["tampered"] = True
        event.detail = edited_detail
        db.commit()

    response = client.get(f"/ops/requests/{request_id}/audit/verify")

    assert response.status_code == 200
    body = response.json()
    assert body["audit_ledger"]["valid"] is False
    assert body["audit_ledger"]["failures"]


def test_audit_ledger_detects_delete():
    request_id = create_request()

    with SessionLocal() as db:
        events = db.query(AuditEvent).filter(AuditEvent.request_id == request_id).order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc()).all()
        assert len(events) >= 2
        db.delete(events[0])
        db.commit()

    response = client.get(f"/ops/requests/{request_id}/audit/verify")

    assert response.status_code == 200
    body = response.json()
    assert body["audit_ledger"]["valid"] is False
    assert body["audit_ledger"]["failures"]
