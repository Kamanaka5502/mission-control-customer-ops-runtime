from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_end_to_end_customer_operations_path():
    customer = {"id": "test-customer", "name": "Test Customer", "industry": "operations"}
    workflow = {"id": "test-workflow", "customer_id": "test-customer", "name": "Test Workflow", "description": "E2E workflow"}

    assert client.post("/ops/customers", json=customer).status_code == 200
    assert client.post("/ops/workflows", json=workflow).status_code == 200

    payload = {
        "customer_id": "test-customer",
        "workflow_id": "test-workflow",
        "request_id": "REQ-E2E-TEST-001",
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

    review = client.post("/ops/requests/REQ-E2E-TEST-001/review", json={"actor": "tester", "decision": "approve", "notes": "ok"})
    assert review.status_code == 200
    assert review.json()["lifecycle_status"] == "approved_for_execution"

    receipt = client.get("/ops/requests/REQ-E2E-TEST-001/receipt")
    assert receipt.status_code == 200
    assert receipt.json()["receipt_id"] == "receipt-REQ-E2E-TEST-001"

    same = client.post("/ops/requests/REQ-E2E-TEST-001/replay/same-condition")
    assert same.status_code == 200
    assert same.json()["matched"] is True

    changed = client.post("/ops/requests/REQ-E2E-TEST-001/replay/changed-condition")
    assert changed.status_code == 200
    assert changed.json()["no_bind_status"] is True

    audit = client.get("/ops/requests/REQ-E2E-TEST-001/audit")
    assert audit.status_code == 200
    assert len(audit.json()) >= 4

    dashboard = client.get("/ops/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["total_requests"] >= 1
