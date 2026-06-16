# Mission Control: Customer Operations Runtime

A deployable customer operations platform for workflow intake, evidence collection, approval orchestration, governed execution, audit trails, receipts, replay, and operational observability.

This is built as a Forward Deployed Engineering portfolio system: a customer-facing application that turns ambiguous operational requests into structured, reviewable, executable workflows.

## What this system does

1. Customer submits an operational request.
2. System creates a structured request envelope.
3. Evidence and context are attached.
4. Runtime policy evaluates readiness and risk.
5. Approval routing determines whether human review is required.
6. Outcome becomes `ADMIT`, `HOLD`, `ESCALATE`, or `REFUSE`.
7. Receipt is generated.
8. Replay verifies same-condition and changed-condition behavior.
9. Dashboard exposes operational state.

## Example use cases

- Vendor onboarding
- Payment approvals
- Security exceptions
- Change management
- Customer operations
- Compliance workflows
- AI-assisted operational decisions

## Forward Deployed Engineering Signals

- Customer workflow intake
- FastAPI backend
- Production-oriented API design
- Structured request schemas
- Runtime policy gate
- Approval and escalation logic
- Receipt and replay system
- Dockerized deployment
- Frontend dashboard scaffold
- Customer discovery docs
- Seeded demo cases

## Quickstart

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API docs:

```text
http://127.0.0.1:8000/docs
```

Run demo cases:

```bash
cd backend
python scripts/run_demo_cases.py
```

Docker:

```bash
docker compose up --build
```

## Core outcomes

- `ADMIT`: request may proceed under current conditions.
- `HOLD`: request needs more evidence, scope review, or correction.
- `ESCALATE`: request requires higher authority or approval.
- `REFUSE`: request cannot proceed and no protected effect is released.

## Build roadmap

### v0.1
- FastAPI API
- Request intake
- Decision engine
- Receipts
- Replay
- Demo customer workflows

### v0.2
- Postgres persistence
- SQLAlchemy models
- Approval queue
- Customer dashboard

### v0.3
- AI-assisted recommendations
- Evidence extraction
- Customer-specific policy packs
- Multi-tenant support

### v1.0
- Auth
- Metrics
- Audit exports
- Deployment hardening
- Production-ready API surface
