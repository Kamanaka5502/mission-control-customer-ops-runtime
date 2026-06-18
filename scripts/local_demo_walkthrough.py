#!/usr/bin/env python3
"""Run the local Mission Control demo walkthrough against a running API."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any


def timestamp_suffix() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


class DemoClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        data = None
        headers = {"Content-Type": "application/json", "x-correlation-id": f"demo-{timestamp_suffix()}"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(f"{self.base_url}{path}", data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10) as res:
                raw = res.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8")
            raise RuntimeError(f"{method} {path} failed with {exc.code}: {body}") from exc

    def get(self, path: str) -> Any:
        return self.request("GET", path)

    def post(self, path: str, payload: dict[str, Any] | None = None) -> Any:
        return self.request("POST", path, payload or {})


def wait_for_api(client: DemoClient, attempts: int = 30) -> None:
    for _ in range(attempts):
        try:
            health = client.get("/health")
            if health.get("status") == "ok":
                return
        except Exception:
            time.sleep(1)
    raise RuntimeError("API did not become healthy. Start it with: docker compose up --build")


def print_step(number: int, title: str, payload: Any) -> None:
    print(f"\n[{number}] {title}")
    print(json.dumps(payload, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Mission Control local demo walkthrough.")
    parser.add_argument("--api", default="http://127.0.0.1:8000", help="Mission Control API base URL")
    args = parser.parse_args()

    client = DemoClient(args.api)
    suffix = timestamp_suffix()
    customer_id = f"demo-customer-{suffix}"
    workflow_id = f"security-exception-{suffix}"
    request_id = f"REQ-DEMO-{suffix}"

    wait_for_api(client)

    customer = client.post("/ops/customers", {"id": customer_id, "name": "Demo Customer", "industry": "operations"})
    print_step(1, "Customer created", customer)

    workflow = client.post(
        "/ops/workflows",
        {"id": workflow_id, "customer_id": customer_id, "name": "Security Exception", "description": "Emergency access review workflow"},
    )
    print_step(2, "Workflow created", workflow)

    decision = client.post(
        "/ops/requests/evaluate",
        {
            "customer_id": customer_id,
            "workflow_id": workflow_id,
            "request_id": request_id,
            "requested_action": "grant_emergency_production_access",
            "business_context": "On-call engineer needs temporary access to resolve an active incident.",
            "authority_present": True,
            "scope_matched": True,
            "evidence_present": True,
            "evidence_fresh": True,
            "risk_level": "critical",
            "approval_required": True,
            "metadata": {"incident_id": f"INC-{suffix}", "requested_duration_minutes": 30},
        },
    )
    print_step(3, "Request evaluated", decision)

    evidence = client.post(
        "/ops/evidence",
        {
            "id": f"evidence-{request_id}",
            "request_id": request_id,
            "label": "incident-ticket",
            "source": "demo-runbook",
            "freshness_status": "fresh",
            "payload": {"incident_id": f"INC-{suffix}", "approver_group": "production-operations"},
        },
    )
    print_step(4, "Evidence attached", evidence)

    review = client.post(
        f"/ops/requests/{request_id}/review",
        {"actor": "demo-reviewer", "decision": "approve", "notes": "Demo approval after evidence review."},
    )
    print_step(5, "Review approved", review)

    execution = client.post(f"/ops/requests/{request_id}/execute")
    print_step(6, "Controlled execution released", execution)

    receipt = client.get(f"/ops/requests/{request_id}/receipt")
    print_step(7, "Receipt generated", {"receipt_id": receipt.get("receipt_id"), "signature_valid": bool(receipt.get("signature"))})

    same_replay = client.post(f"/ops/requests/{request_id}/replay/same-condition")
    changed_replay = client.post(f"/ops/requests/{request_id}/replay/changed-condition")
    print_step(8, "Replay checked", {"same_condition_matched": same_replay.get("matched"), "changed_condition_outcome": changed_replay.get("observed_outcome")})

    audit = client.get(f"/ops/requests/{request_id}/audit/verify")
    print_step(9, "Audit ledger verified", audit)

    proof_export = client.post(f"/ops/requests/{request_id}/proof-bundle")
    proof_verify = client.get(f"/ops/requests/{request_id}/proof-bundle/verify")
    print_step(10, "Proof bundle exported and verified", {"export": proof_export, "verify": proof_verify})

    dashboard = client.get("/ops/dashboard")
    print_step(11, "Dashboard refreshed", dashboard)

    print("\nDemo capture path:")
    print("Dashboard -> request intake -> runtime decision -> review -> execution -> receipt -> replay -> audit -> proof bundle")
    print(f"Request id: {request_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
