from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.services.rbac import Role, create_auth_token

client = TestClient(app)
TEST_SECRET = "0123456789abcdef0123456789abcdef"


def auth_headers(role: Role, actor_id: str, scopes: list[str] | None = None) -> dict[str, str]:
    token = create_auth_token(actor_id=actor_id, role=role, scopes=scopes, secret=TEST_SECRET)
    return {"authorization": f"Bearer {token}"}


def enable_auth(monkeypatch):
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    monkeypatch.setenv("AUTH_TOKEN_SECRET", TEST_SECRET)


def make_authenticated_request(monkeypatch):
    enable_auth(monkeypatch)
    suffix = uuid4().hex[:8]
    customer_id = f"auth-customer-{suffix}"
    workflow_id = f"auth-workflow-{suffix}"
    request_id = f"REQ-AUTH-{suffix}"

    admin = auth_headers(Role.ADMIN, "admin-test")
    requester = auth_headers(Role.REQUESTER, "requester-test")

    customer = client.post(
        "/ops/customers",
        headers=admin,
        json={"id": customer_id, "name": "Auth Customer", "industry": "operations"},
    )
    assert customer.status_code in {200, 201}

    workflow = client.post(
        "/ops/workflows",
        headers=admin,
        json={"id": workflow_id, "customer_id": customer_id, "name": "Auth Workflow", "description": "Auth workflow"},
    )
    assert workflow.status_code in {200, 201}

    response = client.post(
        "/ops/requests/evaluate",
        headers=requester,
        json={
            "customer_id": customer_id,
            "workflow_id": workflow_id,
            "request_id": request_id,
            "requested_action": "approve_authenticated_action",
            "business_context": "Authenticated RBAC test request",
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


def test_auth_required_for_protected_routes(monkeypatch):
    enable_auth(monkeypatch)
    response = client.post(
        "/ops/requests/evaluate",
        json={
            "customer_id": "missing",
            "workflow_id": "missing",
            "request_id": "REQ-NO-AUTH",
            "requested_action": "denied",
            "business_context": "Denied before mutation",
            "authority_present": True,
            "scope_matched": True,
            "evidence_present": True,
            "evidence_fresh": True,
            "risk_level": "low",
            "approval_required": False,
            "metadata": {},
        },
    )
    assert response.status_code == 401


def test_rbac_requester_cannot_approve(monkeypatch):
    request_id = make_authenticated_request(monkeypatch)
    response = client.post(
        f"/ops/requests/{request_id}/review",
        headers=auth_headers(Role.REQUESTER, "requester-test"),
        json={"actor": "requester-test", "decision": "approve", "notes": "should fail"},
    )
    assert response.status_code == 403


def test_rbac_reviewer_cannot_execute_without_permission(monkeypatch):
    request_id = make_authenticated_request(monkeypatch)
    response = client.post(
        f"/ops/requests/{request_id}/execute",
        headers=auth_headers(Role.REVIEWER, "reviewer-test"),
    )
    assert response.status_code == 403


def test_auditor_cannot_mutate_state(monkeypatch):
    request_id = make_authenticated_request(monkeypatch)
    response = client.post(
        f"/ops/requests/{request_id}/review",
        headers=auth_headers(Role.AUDITOR, "auditor-test"),
        json={"actor": "auditor-test", "decision": "approve", "notes": "should fail"},
    )
    assert response.status_code == 403


def test_service_account_cannot_exceed_scope(monkeypatch):
    request_id = make_authenticated_request(monkeypatch)
    service_headers = auth_headers(Role.SERVICE_ACCOUNT, "svc-receipt-reader", scopes=["receipt:read"])

    receipt = client.get(f"/ops/requests/{request_id}/receipt", headers=service_headers)
    assert receipt.status_code == 200

    review = client.post(
        f"/ops/requests/{request_id}/review",
        headers=service_headers,
        json={"actor": "svc-receipt-reader", "decision": "approve", "notes": "should fail"},
    )
    assert review.status_code == 403
