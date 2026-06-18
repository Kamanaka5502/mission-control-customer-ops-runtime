from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def create_request():
    suffix = uuid4().hex[:8]
    customer_id = f"integrity-customer-{suffix}"
    workflow_id = f"integrity-workflow-{suffix}"
    request_id = f"REQ-INTEGRITY-{suffix}"

    customer = client.post(
        "/ops/customers",
        json={"id": customer_id, "name": "Integrity Customer", "industry": "operations"},
    )
    assert customer.status_code in {200, 201}

    workflow = client.post(
        "/ops/workflows",
        json={"id": workflow_id, "customer_id": customer_id, "name": "Integrity Workflow", "description": "Integrity workflow"},
    )
    assert workflow.status_code in {200, 201}

    evaluated = client.post(
        "/ops/requests/evaluate",
        json={
            "customer_id": customer_id,
            "workflow_id": workflow_id,
            "request_id": request_id,
            "requested_action": "approve_integrity_action",
            "business_context": "Integrity hash test request",
            "authority_present": True,
            "scope_matched": True,
            "evidence_present": True,
            "evidence_fresh": True,
            "risk_level": "low",
            "approval_required": False,
            "metadata": {"purpose": "integrity-test"},
        },
    )
    assert evaluated.status_code == 200
    return request_id


def test_request_snapshot_is_captured_and_verified():
    request_id = create_request()

    response = client.get(f"/ops/requests/{request_id}/integrity")

    assert response.status_code == 200
    body = response.json()
    assert body["request_snapshot"]["captured"] is True
    assert body["request_snapshot"]["match"] is True
    assert body["request_snapshot"]["captured_hash"] == body["request_snapshot"]["current_hash"]
    assert body["evidence_manifest"]["evidence_count"] == 0
    assert body["integrity_status"] == "VERIFIED"


def test_evidence_manifest_is_captured_after_evidence_attachment():
    request_id = create_request()

    attached = client.post(
        "/ops/evidence",
        json={
            "id": f"evidence-{uuid4().hex[:8]}",
            "request_id": request_id,
            "label": "approval packet",
            "source": "test-suite",
            "freshness_status": "current",
            "payload": {"document": "approval", "version": 1},
        },
    )
    assert attached.status_code == 200

    response = client.get(f"/ops/requests/{request_id}/integrity")

    assert response.status_code == 200
    body = response.json()
    assert body["request_snapshot"]["match"] is True
    assert body["evidence_manifest"]["captured"] is True
    assert body["evidence_manifest"]["match"] is True
    assert body["evidence_manifest"]["evidence_count"] == 1
    assert body["integrity_status"] == "VERIFIED"
