# Mission Control: Customer Operations Runtime

A working customer operations platform for workflow intake, evidence collection, review orchestration, governed execution status, audit trails, receipts, replay, and operational observability.

This is built as a Forward Deployed Engineering portfolio system: a customer-facing application that turns ambiguous operational requests into structured, reviewable, executable workflows.

## Current state

This repo is no longer only a scaffold. It includes an end-to-end v0.3 runtime:

- FastAPI backend
- SQLAlchemy persistence
- SQLite default database
- customer and workflow APIs
- request evaluation API
- evidence attachment API
- review action API
- persisted receipt endpoint
- persisted replay endpoints
- audit trail endpoint
- dashboard API
- Next.js frontend dashboard
- Docker Compose deployment
- GitHub Actions CI
- smoke test script
- end-to-end API test

## Operational path

```text
customer
  -> workflow
  -> request intake
  -> persisted request
  -> runtime decision
  -> review action
  -> receipt
  -> same-condition replay
  -> changed-condition replay
  -> audit trail
  -> dashboard
```

## What this system does

1. Customer submits an operational request.
2. System creates a structured request envelope.
3. Evidence and context can be attached.
4. Runtime policy evaluates readiness and risk.
5. Review routing determines whether human action is required.
6. Outcome becomes `ADMIT`, `HOLD`, `ESCALATE`, or `REFUSE`.
7. Receipt is generated.
8. Replay verifies same-condition and changed-condition behavior.
9. Audit trail records material events.
10. Dashboard exposes operational state.

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
- Review and escalation logic
- Receipt and replay system
- Persistent audit trail
- Dockerized deployment
- Frontend dashboard
- Customer discovery docs
- Seeded demo cases
- CI and tests

## Quickstart: Docker

```bash
docker compose up --build
```

Open:

```text
Frontend: http://localhost:3000
API docs: http://localhost:8000/docs
Health: http://localhost:8000/health
```

In the frontend, click:

```text
Seed Demo Customer
```

Then submit a customer request and inspect decision, receipt, replay, audit trail, and dashboard state.

## Quickstart: backend only

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python scripts/seed_demo_data.py
uvicorn app.main:app --reload
```

Run demo cases:

```bash
python scripts/run_demo_cases.py
```

Run smoke test while API is running:

```bash
python scripts/smoke_test.py
```

Run tests:

```bash
pytest -q
```

## Quickstart: frontend only

```bash
cd frontend
npm install
npm run dev
```

Set API base if needed:

```bash
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
```

## Core outcomes

- `ADMIT`: request may proceed under current conditions.
- `HOLD`: request needs more evidence, scope review, or correction.
- `ESCALATE`: request requires higher authority or approval.
- `REFUSE`: request cannot proceed and no protected effect is released.

## Key docs

- `docs/end-to-end-runbook.md`
- `docs/customer-discovery.md`
- `docs/architecture.md`
- `docs/completeness-checklist.md`

## Production hardening roadmap

- real authentication
- role-based access control
- PostgreSQL production profile
- file upload-backed evidence storage
- structured logging and request correlation IDs
- metrics endpoint
- multi-tenant isolation enforcement
- deployment target docs
- API versioning
- frontend error-state polish
