# End-to-End Runbook

This runbook validates the full Mission Control Customer Operations Runtime path.

## 1. Start the system

```bash
docker compose up --build
```

Services:

- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Frontend: `http://localhost:3000`

## 2. Seed demo customer

From the frontend, click:

```text
Seed Demo Customer
```

Or from backend:

```bash
cd backend
python scripts/seed_demo_data.py
```

## 3. Submit a request

Use the frontend request form or call:

```bash
curl -X POST http://localhost:8000/ops/requests/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "demo-customer",
    "workflow_id": "vendor-onboarding",
    "request_id": "REQ-E2E-001",
    "requested_action": "approve_vendor_for_low_risk_service",
    "business_context": "Vendor completed intake with fresh evidence.",
    "authority_present": true,
    "scope_matched": true,
    "evidence_present": true,
    "evidence_fresh": true,
    "risk_level": "low",
    "approval_required": false,
    "metadata": {"source": "runbook"}
  }'
```

Expected:

```text
ADMIT
AUTHORIZED_TO_PROCEED
no_bind_status = false
```

## 4. Review request

```bash
curl -X POST http://localhost:8000/ops/requests/REQ-E2E-001/review \
  -H "Content-Type: application/json" \
  -d '{"actor":"ops-reviewer","decision":"approve","notes":"Approved in runbook."}'
```

Expected lifecycle status:

```text
approved_for_execution
```

## 5. Load receipt

```bash
curl http://localhost:8000/ops/requests/REQ-E2E-001/receipt
```

Expected receipt fields:

- receipt_id
- request_id
- workflow_id
- outcome
- protected_effect_status
- no_bind_status
- replay_token
- public_hash

## 6. Same-condition replay

```bash
curl -X POST http://localhost:8000/ops/requests/REQ-E2E-001/replay/same-condition
```

Expected:

```text
matched = true
observed_outcome = ADMIT
```

## 7. Changed-condition replay

```bash
curl -X POST http://localhost:8000/ops/requests/REQ-E2E-001/replay/changed-condition
```

Expected:

```text
changed_conditions includes authority_removed, evidence_stale, risk_high
observed_outcome changes away from the original authorization posture
```

## 8. Audit trail

```bash
curl http://localhost:8000/ops/requests/REQ-E2E-001/audit
```

Expected audit events:

- request_evaluated
- review_action
- receipt_viewed
- same_condition_replay
- changed_condition_replay

## 9. Dashboard

```bash
curl http://localhost:8000/ops/dashboard
```

Expected:

- total request count
- outcome counts
- pending review count
- recent requests

## End-to-end success condition

A customer request can move through:

```text
intake -> persisted request -> runtime decision -> review -> receipt -> replay -> audit -> dashboard
```

This is a working customer operations runtime, not a static proof surface.
