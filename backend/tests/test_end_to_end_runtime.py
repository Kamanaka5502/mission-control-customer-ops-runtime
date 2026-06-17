from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_end_to_end_customer_operations_path():
    suffix = uuid4().hex[:8]
    customer_id = f"test-customer-{suffix}"
    workflow_id = f"test-workflow-{suffix}"
    request_id = f"REQ-E2E-TEST-{suffix}"

    customer = {"id": customer_id, "name": "Test Customer", "industry": "operations"}
    workflow = {"id": workflow_id, "customer_id": customer_id, "name": "Test Workflow", "description": "E2E workflow"}

    assert client.post("/ops/customers", json=customer).status_code == 200
    assert client.post("/ops/workflows", json=workflow).status_code == 200

    payload = {
        "customer_id": customer_id,
        "workflow_id": workflow_id,
        "request_id": request_id,
        "requested_action": "approve_test_action",
        "business_context": "E2E test request",
        "authority_present": True,
        "scope_matched": True,
        "evidence_present": True,
        "evidence_fresh": True,
        "risk_level": "low",
        "approval_required": False,
        "metadata": {"test": True}
    }

    decision = client.post("/ops/requests/evaluate", json=payload)
    assert decision.status_code == 200
    assert decision.json()["outcome"] == "ADMIT"

    review = client.post(f"/ops/requests/{request_id}/review", json={"actor": "tester", "decision": "approve", "notes": "ok"})
    assert review.status_code == 200
    assert review.json()["lifecycle_status"] == "approved_for_execution"

    receipt = client.get(f"/ops/requests/{request_id}/receipt")
    assert receipt.status_code == 200
    assert receipt.json()["receipt_id"] == f"receipt-{request_id}"

    same = client.post(f"/ops/requests/{request_id}/replay/same-condition")
    assert same.status_code == 200
    assert same.json()["matched"] is True

    changed = client.post(f"/ops/requests/{request_id}/replay/changed-condition")
    assert changed.status_code == 200
    assert changed.json()["no_bind_status"] is True

    audit = client.get(f"/ops/requests/{request_id}/audit")
    assert audit.status_code == 200
    assert len(audit.json()) >= 4

    dashboard = client.get("/ops/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["total_requests"] >= 1
