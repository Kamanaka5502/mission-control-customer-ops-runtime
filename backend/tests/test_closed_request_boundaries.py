from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def make_closed_request():
    suffix = uuid4().hex[:8]
    customer_id = f"closed-customer-{suffix}"
    workflow_id = f"closed-workflow-{suffix}"
    request_id = f"REQ-CLOSED-{suffix}"

    client.post(
        "/ops/customers",
        headers={"x-actor-role": "admin", "x-tenant-id": customer_id},
        json={"id": customer_id, "name": "Closed Customer", "industry": "operations"},
    )
    client.post(
        "/ops/workflows",
        headers={"x-actor-role": "admin", "x-tenant-id": customer_id},
        json={"id": workflow_id, "customer_id": customer_id, "name": "Closed Workflow", "description": "Closed workflow"},
    )
    response = client.post(
        "/ops/requests/evaluate",
        headers={"x-actor-role": "operator", "x-tenant-id": customer_id},
        json={
            "customer_id": customer_id,
            "workflow_id": workflow_id,
            "request_id": request_id,
            "requested_action": "release_closed_action",
            "business_context": "Closed request boundary test",
            "authority_present": False,
            "scope_matched": True,
            "evidence_present": True,
            "evidence_fresh": True,
            "risk_level": "low",
            "approval_required": False,
            "metadata": {},
        },
    )
    assert response.status_code == 200
    assert response.json()["outcome"] == "REFUSE"
    return request_id, customer_id


def test_closed_request_cannot_be_approved():
    request_id, tenant_id = make_closed_request()

    response = client.post(
        f"/ops/requests/{request_id}/review",
        headers={"x-actor-role": "reviewer", "x-tenant-id": tenant_id},
        json={"actor": "reviewer", "decision": "approve", "notes": "should remain closed"},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["review_status"] == "BLOCKED"


def test_closed_request_cannot_execute():
    request_id, tenant_id = make_closed_request()

    response = client.post(
        f"/ops/requests/{request_id}/execute",
        headers={"x-actor-role": "operator", "x-tenant-id": tenant_id},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["execution_status"] == "BLOCKED"


def test_closed_request_queues_as_blocked_job():
    request_id, tenant_id = make_closed_request()

    response = client.post(
        f"/ops/jobs/{request_id}/queue",
        headers={"x-actor-role": "operator", "x-tenant-id": tenant_id},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "BLOCKED"
