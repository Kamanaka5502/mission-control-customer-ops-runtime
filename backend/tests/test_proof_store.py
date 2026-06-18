from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.proof_store import proof_bundle_path

client = TestClient(app)


def create_request():
    suffix = uuid4().hex[:8]
    customer_id = f"proof-customer-{suffix}"
    workflow_id = f"proof-workflow-{suffix}"
    request_id = f"REQ-PROOF-{suffix}"

    customer = client.post(
        "/ops/customers",
        json={"id": customer_id, "name": "Proof Customer", "industry": "operations"},
    )
    assert customer.status_code in {200, 201}

    workflow = client.post(
        "/ops/workflows",
        json={"id": workflow_id, "customer_id": customer_id, "name": "Proof Workflow", "description": "Proof workflow"},
    )
    assert workflow.status_code in {200, 201}

    evaluated = client.post(
        "/ops/requests/evaluate",
        json={
            "customer_id": customer_id,
            "workflow_id": workflow_id,
            "request_id": request_id,
            "requested_action": "approve_proof_action",
            "business_context": "Proof bundle test request",
            "authority_present": True,
            "scope_matched": True,
            "evidence_present": True,
            "evidence_fresh": True,
            "risk_level": "low",
            "approval_required": False,
            "metadata": {"purpose": "proof-bundle-test"},
        },
    )
    assert evaluated.status_code == 200
    return request_id


def test_proof_bundle_export_persists_and_verifies(tmp_path, monkeypatch):
    monkeypatch.setenv("PROOF_STORE_PATH", str(tmp_path))
    request_id = create_request()

    exported = client.post(f"/ops/requests/{request_id}/proof-bundle")

    assert exported.status_code == 200
    export_body = exported.json()
    assert export_body["storage"]["stored"] is True
    assert export_body["verification"]["valid"] is True

    stored = client.get(f"/ops/requests/{request_id}/proof-bundle")
    assert stored.status_code == 200
    bundle = stored.json()
    assert bundle["request_id"] == request_id
    assert bundle["proof_hash"] == export_body["proof_hash"]
    assert bundle["receipt_verification"]["valid"] is True
    assert bundle["audit_ledger"]["valid"] is True

    verified = client.get(f"/ops/requests/{request_id}/proof-bundle/verify")
    assert verified.status_code == 200
    assert verified.json()["verification"]["valid"] is True


def test_proof_bundle_contains_required_artifacts(tmp_path, monkeypatch):
    monkeypatch.setenv("PROOF_STORE_PATH", str(tmp_path))
    request_id = create_request()

    client.post(f"/ops/requests/{request_id}/proof-bundle")
    bundle = client.get(f"/ops/requests/{request_id}/proof-bundle").json()

    assert "request_snapshot" in bundle
    assert "evidence_manifest" in bundle
    assert "decision" in bundle
    assert "receipt" in bundle
    assert "replay_result" in bundle
    assert "audit_ledger" in bundle
    assert "integrity" in bundle
    assert bundle["receipt"]["request_snapshot_hash"] == bundle["request_snapshot"]["snapshot_hash"]
    assert bundle["receipt"]["evidence_manifest_hash"] == bundle["evidence_manifest"]["manifest_hash"]


@pytest.mark.parametrize("request_id", ["../escape", "nested/path", "bad\\path", "bad path"])
def test_proof_bundle_path_rejects_unsafe_request_ids(tmp_path, request_id):
    with pytest.raises(ValueError):
        proof_bundle_path(request_id, base_dir=tmp_path)
