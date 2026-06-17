from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def create_request_for_customer(customer_id: str):
    suffix = uuid4().hex[:8]
    workflow_id = f"workflow-{customer_id}-{suffix}"
    request_id = f"REQ-{customer_id}-{suffix}"

    client.post(
        "/ops/customers",
        headers={"x-actor-role": "admin", "x-tenant-id": customer_id},
        json={"id": customer_id, "name": customer_id, "industry": "operations"},
    )
    client.post(
        "/ops/workflows",
        headers={"x-actor-role": "admin", "x-tenant-id": customer_id},
        json={"id": workflow_id, "customer_id": customer_id, "name": "Tenant Workflow", "description": "Tenant workflow"},
    )
    response = client.post(
        "/ops/requests/evaluate",
        headers={"x-actor-role": "operator", "x-tenant-id": customer_id},
        json={
            "customer_id": customer_id,
            "workflow_id": workflow_id,
            "request_id": request_id,
            "requested_action": "tenant_scoped_action",
            "business_context": "Tenant test",
            "authority_present": True,
            "scope_matched": True,
            "evidence_present": True,
            "evidence_fresh": True,
            "risk_level": "low",
            "approval_required": False,
            "metadata": {},
        },
    )
    assert response.status_code == 200
    return request_id


def test_tenant_can_read_own_request():
    request_id = create_request_for_customer("tenant-a")
    response = client.get(
        f"/ops/requests/{request_id}",
        headers={"x-actor-role": "auditor", "x-tenant-id": "tenant-a"},
    )
    assert response.status_code == 200
    assert response.json()["customer_id"] == "tenant-a"


def test_cross_tenant_request_access_is_denied():
    request_id = create_request_for_customer("tenant-b")
    response = client.get(
        f"/ops/requests/{request_id}",
        headers={"x-actor-role": "auditor", "x-tenant-id": "tenant-c"},
    )
    assert response.status_code == 403


def test_cross_tenant_receipt_access_is_denied():
    request_id = create_request_for_customer("tenant-d")
    response = client.get(
        f"/ops/requests/{request_id}/receipt",
        headers={"x-actor-role": "auditor", "x-tenant-id": "tenant-e"},
    )
    assert response.status_code == 403


def test_dashboard_is_tenant_scoped():
    create_request_for_customer("tenant-f")
    create_request_for_customer("tenant-g")

    response = client.get(
        "/ops/dashboard",
        headers={"x-actor-role": "auditor", "x-tenant-id": "tenant-f"},
    )
    assert response.status_code == 200
    assert all(item["customer_id"] == "tenant-f" for item in response.json()["recent_requests"])


def test_customer_list_is_tenant_scoped():
    create_request_for_customer("tenant-h")
    create_request_for_customer("tenant-i")

    response = client.get(
        "/ops/customers",
        headers={"x-actor-role": "auditor", "x-tenant-id": "tenant-h"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == "tenant-h"
