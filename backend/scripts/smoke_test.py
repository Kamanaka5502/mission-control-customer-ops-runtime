import json
import urllib.request

BASE = "http://127.0.0.1:8000"


def post(path: str, payload: dict):
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read().decode("utf-8"))


def get(path: str):
    with urllib.request.urlopen(f"{BASE}{path}") as res:
        return json.loads(res.read().decode("utf-8"))


def main():
    suffix = "SMOKE-001"
    post("/ops/customers", {"id": "smoke-customer", "name": "Smoke Customer", "industry": "operations"})
    post("/ops/workflows", {"id": "smoke-workflow", "customer_id": "smoke-customer", "name": "Smoke Workflow", "description": "Smoke workflow"})
    decision = post("/ops/requests/evaluate", {
        "customer_id": "smoke-customer",
        "workflow_id": "smoke-workflow",
        "request_id": f"REQ-{suffix}",
        "requested_action": "approve_smoke_action",
        "business_context": "Smoke test request",
        "authority_present": True,
        "scope_matched": True,
        "evidence_present": True,
        "evidence_fresh": True,
        "risk_level": "low",
        "approval_required": False,
        "metadata": {"source": "smoke_test"}
    })
    assert decision["outcome"] == "ADMIT"
    receipt = get(f"/ops/requests/REQ-{suffix}/receipt")
    same = post(f"/ops/requests/REQ-{suffix}/replay/same-condition", {})
    changed = post(f"/ops/requests/REQ-{suffix}/replay/changed-condition", {})
    audit = get(f"/ops/requests/REQ-{suffix}/audit")
    dashboard = get("/ops/dashboard")
    print(json.dumps({
        "decision": decision["outcome"],
        "receipt": receipt["receipt_id"],
        "same_replay_matched": same["matched"],
        "changed_replay_outcome": changed["observed_outcome"],
        "audit_events": len(audit),
        "dashboard_total": dashboard["total_requests"]
    }, indent=2))


if __name__ == "__main__":
    main()
