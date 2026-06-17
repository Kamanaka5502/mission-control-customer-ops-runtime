from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def make_executable_request():
    suffix = uuid4().hex[:8]
    customer_id = f"job-customer-{suffix}"
    workflow_id = f"job-workflow-{suffix}"
    request_id = f"REQ-JOB-{suffix}"

    client.post("/ops/customers", headers={"x-actor-role": "admin", "x-tenant-id": customer_id}, json={"id": customer_id, "name": "Job Customer", "industry": "operations"})
    client.post("/ops/workflows", headers={"x-actor-role": "admin", "x-tenant-id": customer_id}, json={"id": workflow_id, "customer_id": customer_id, "name": "Job Workflow", "description": "Job workflow"})
    response = client.post(
        "/ops/requests/evaluate",
        headers={"x-actor-role": "operator", "x-tenant-id": customer_id},
        json={
            "customer_id": customer_id,
            "workflow_id": workflow_id,
            "request_id": request_id,
            "requested_action": "execute_job_action",
            "business_context": "Execution job test",
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
    return request_id, customer_id


def test_queue_claim_complete_job():
    request_id, tenant_id = make_executable_request()

    queued = client.post(f"/ops/jobs/{request_id}/queue", headers={"x-actor-role": "operator", "x-tenant-id": tenant_id})
    assert queued.status_code == 200
    assert queued.json()["status"] == "QUEUED"

    job_id = queued.json()["id"]

    running = client.post(f"/ops/jobs/{job_id}/claim", headers={"x-actor-role": "operator"})
    assert running.status_code == 200
    assert running.json()["status"] == "RUNNING"

    completed = client.post(f"/ops/jobs/{job_id}/complete", headers={"x-actor-role": "operator"})
    assert completed.status_code == 200
    assert completed.json()["status"] == "COMPLETED"


def test_fail_job():
    request_id, tenant_id = make_executable_request()

    queued = client.post(f"/ops/jobs/{request_id}/queue", headers={"x-actor-role": "operator", "x-tenant-id": tenant_id})
    job_id = queued.json()["id"]

    failed = client.post(f"/ops/jobs/{job_id}/fail?failure_reason=worker_error", headers={"x-actor-role": "operator"})
    assert failed.status_code == 200
    assert failed.json()["status"] == "FAILED"
    assert failed.json()["failure_reason"] == "worker_error"


def test_auditor_cannot_queue_job():
    request_id, tenant_id = make_executable_request()

    response = client.post(f"/ops/jobs/{request_id}/queue", headers={"x-actor-role": "auditor", "x-tenant-id": tenant_id})
    assert response.status_code == 403
