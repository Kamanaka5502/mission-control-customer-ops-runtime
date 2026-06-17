from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def make_request():
    suffix = uuid4().hex[:8]
    customer_id = f"rbac-customer-{suffix}"
    workflow_id = f"rbac-workflow-{suffix}"
    request_id = f"REQ-RBAC-{suffix}"

    client.post("/ops/customers", json={"id": customer_id, "name": "RBAC Customer", "industry": "operations"})
    client.post("/ops/workflows", json={"id": workflow_id, "customer_id": customer_id, "name": "RBAC Workflow", "description": "RBAC workflow"})

    response = client.post(
        "/ops/requests/evaluate",
        headers={"x-actor-role": "operator"},
        json={
            "customer_id": customer_id,
            "workflow_id": workflow_id,
            "request_id": request_id,
            "requested_action": "approve_rbac_action",
            "business_context": "RBAC test request",
            "authority_present": True,
            "scope_matched": True,
            "evidence_present": True,
            "evidence_fresh": True,
            "risk_level": "low",
            "approval_required": False,
            "metadata": {"test": True},
        },
    )
    assert response.status_code == 200
    return request_id


def test_operator_can_create_request():
    request_id = make_request()
    assert request_id.startswith("REQ-RBAC-")


def test_auditor_cannot_create_request():
    response = client.post(
        "/ops/requests/evaluate",
        headers={"x-actor-role": "auditor"},
        json={
            "customer_id": "missing",
            "workflow_id": "missing",
            "request_id": "REQ-DENIED",
            "requested_action": "denied",
            "business_context": "Denied",
            "authority_present": True,
            "scope_matched": True,
            "evidence_present": True,
            "evidence_fresh": True,
            "risk_level": "low",
            "approval_required": False,
            "metadata": {},
        },
    )
    assert response.status_code == 403


def test_reviewer_can_review_request():
    request_id = make_request()
    response = client.post(
        f"/ops/requests/{request_id}/review",
        headers={"x-actor-role": "reviewer"},
        json={"actor": "reviewer", "decision": "approve", "notes": "approved"},
    )
    assert response.status_code == 200
    assert response.json()["lifecycle_status"] == "approved_for_execution"


def test_operator_cannot_review_request():
    request_id = make_request()
    response = client.post(
        f"/ops/requests/{request_id}/review",
        headers={"x-actor-role": "operator"},
        json={"actor": "operator", "decision": "approve", "notes": "should fail"},
    )
    assert response.status_code == 403


def test_auditor_can_view_receipt_but_cannot_execute():
    request_id = make_request()

    receipt = client.get(
        f"/ops/requests/{request_id}/receipt",
        headers={"x-actor-role": "auditor"},
    )
    assert receipt.status_code == 200

    execute = client.post(
        f"/ops/requests/{request_id}/execute",
        headers={"x-actor-role": "auditor"},
    )
    assert execute.status_code == 403


def test_admin_can_execute_request():
    request_id = make_request()
    response = client.post(
        f"/ops/requests/{request_id}/execute",
        headers={"x-actor-role": "admin"},
    )
    assert response.status_code == 200
    assert response.json()["execution_status"] == "EXECUTED"
