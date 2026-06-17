# Forward Deployed Engineering Demo Script

Use this script for a 60–90 second repo walkthrough.

## Opening

Mission Control is a customer operations runtime. It takes ambiguous operational requests and turns them into structured, reviewable, executable workflows.

The point is not just to show a policy decision. The point is to show a full operational lifecycle:

```text
intake -> decision -> review -> controlled execution -> receipt -> replay -> audit -> dashboard
```

## Demo flow

1. Open the dashboard.
2. Click `Seed Demo Customer`.
3. Submit a request.
4. Show the runtime outcome.
5. Approve, hold, escalate, or refuse.
6. Execute only after lifecycle conditions permit release.
7. Load the receipt.
8. Run same-condition replay.
9. Run changed-condition replay.
10. Load the audit trail.
11. Show `/metrics` and `/docs`.

## Talk track

This is the kind of system I would deploy with a customer when the workflow is operationally important but still ambiguous at intake.

The runtime separates request submission from execution. It checks authority, scope, evidence freshness, risk, and review requirements. It then records a decision and prevents controlled execution until the lifecycle state allows release.

The receipt and replay layer exists so the customer can inspect what happened, why it happened, and whether the same or changed conditions reproduce the expected behavior.

## What to emphasize

- working FastAPI backend
- working Next.js dashboard
- persisted workflow state
- review queue behavior
- execution guard
- receipts
- replay
- audit trail
- Dockerized deployment
- tests and CI

## Close

This demonstrates forward-deployed engineering judgment: taking an ambiguous customer workflow and turning it into a usable runtime with API, UI, persistence, controls, auditability, and deployment path.
