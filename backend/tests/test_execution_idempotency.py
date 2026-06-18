from uuid import uuid4

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.db_models import OperationRequest
from app.main import app

client = TestClient(app)


def create_demo_request(*, risk_level: str = "low", approval_required: bool = False) -> str:
    suffix = uuid4().hex[:8]
    customer_id = f"exec-customer-{suffix}"
    workflow_id = f"exec-workflow-{suffix}"
    request_id = f"REQ-EXEC-{suffix}"

    customer = client.post(
        "/ops/customers",
        json={"id": customer_id, "name": "Execution Customer", "industry": "operations"},
    )
    assert customer.status_code in {200, 201}

    workflow = client.post(
        "/ops/workflows",
        json={"id": workflow_id, "customer_id": customer_id, "name": "Execution Workflow", "description": "Execution workflow"},
    )
    assert workflow.status_code in {200, 201}

    evaluated = client.post(
        "/ops/requests/evaluate",
        json={
            "customer_id": customer_id,
            "workflow_id": workflow_id,
            "request_id": request_id,
            "requested_action": "approve_execution_action",
            "business_context": "Execution idempotency test request",
            "authority_present": True,
            "scope_matched": True,
            "evidence_present": True,
            "evidence_fresh": True,
            "risk_level": risk_level,
            "approval_required": approval_required,
            "metadata": {"purpose": "execution-idempotency-test"},
        },
    )
    assert evaluated.status_code == 200
    return request_id


def test_execution_is_idempotent_after_first_release():
    request_id = create_demo_request()

    first = client.post(f"/ops/requests/{request_id}/execute")
    second = client.post(f"/ops/requests/{request_id}/execute")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["execution_status"] == "EXECUTED"
    assert first.json()["idempotent_replay"] is False
    assert second.json()["execution_status"] == "EXECUTED"
    assert second.json()["idempotent_replay"] is True
    assert second.json()["receipt_id"] == first.json()["receipt_id"]

    audit = client.get(f"/ops/requests/{request_id}/audit").json()
    event_types = [event["event_type"] for event in audit]
    assert event_types.count("execution_completed") == 1
    assert event_types.count("execution_idempotent_replay") == 1


def test_final_execution_check_blocks_changed_request_state():
    request_id = create_demo_request()

    db = SessionLocal()
    try:
        operation = db.get(OperationRequest, request_id)
        operation.risk_level = "critical"
        db.commit()
    finally:
        db.close()

    response = client.post(f"/ops/requests/{request_id}/execute")

    assert response.status_code == 409
    assert response.json()["detail"]["execution_status"] == "BLOCKED"
    assert "no longer matches" in response.json()["detail"]["reason"]


def test_execution_metadata_does_not_break_request_integrity():
    request_id = create_demo_request()

    first = client.post(f"/ops/requests/{request_id}/execute")
    assert first.status_code == 200

    integrity = client.get(f"/ops/requests/{request_id}/integrity")
    assert integrity.status_code == 200
    assert integrity.json()["request_snapshot"]["match"] is True
