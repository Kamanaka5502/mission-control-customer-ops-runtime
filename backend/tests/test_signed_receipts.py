from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.services.receipt import verify_receipt_signature

client = TestClient(app)


def create_request():
    suffix = uuid4().hex[:8]
    customer_id = f"signed-customer-{suffix}"
    workflow_id = f"signed-workflow-{suffix}"
    request_id = f"REQ-SIGNED-{suffix}"

    customer = client.post(
        "/ops/customers",
        json={"id": customer_id, "name": "Signed Customer", "industry": "operations"},
    )
    assert customer.status_code in {200, 201}

    workflow = client.post(
        "/ops/workflows",
        json={"id": workflow_id, "customer_id": customer_id, "name": "Signed Workflow", "description": "Signed workflow"},
    )
    assert workflow.status_code in {200, 201}

    evaluated = client.post(
        "/ops/requests/evaluate",
        json={
            "customer_id": customer_id,
            "workflow_id": workflow_id,
            "request_id": request_id,
            "requested_action": "approve_signed_action",
            "business_context": "Signed receipt test request",
            "authority_present": True,
            "scope_matched": True,
            "evidence_present": True,
            "evidence_fresh": True,
            "risk_level": "low",
            "approval_required": False,
            "metadata": {"purpose": "signed-receipt-test"},
        },
    )
    assert evaluated.status_code == 200
    return request_id


def test_receipt_signature_verifies():
    request_id = create_request()

    response = client.get(f"/ops/requests/{request_id}/receipt")

    assert response.status_code == 200
    receipt = response.json()
    assert receipt["signature_algorithm"] == "hmac-sha256"
    assert receipt["signature"]
    assert verify_receipt_signature(receipt)["valid"] is True


def test_tampered_receipt_fails_verification():
    request_id = create_request()
    receipt = client.get(f"/ops/requests/{request_id}/receipt").json()

    receipt["requested_action"] = "tampered_action"

    result = verify_receipt_signature(receipt)
    assert result["valid"] is False
    assert result["hash_matches"] is False
