# Architecture

```text
Customer Request
  -> Structured Envelope
  -> Runtime Policy Gate
  -> Outcome
  -> Receipt
  -> Replay
  -> Operational Dashboard
```

## System role

Mission Control is a customer operations runtime. It is a deployable application pattern for intake, evaluation, approval, operational review, auditability, and replay.

## Components

- FastAPI API
- Customer request schema
- Runtime decision service
- Receipt service
- Replay service
- Demo case runner
- Docker deployment
- Frontend dashboard scaffold

## Next architecture layer

The next implementation pass should add:

- PostgreSQL persistence
- SQLAlchemy models
- auth-ready user and customer model
- approval queue
- workflow timeline
- evidence attachments
- observability middleware
- frontend dashboard
