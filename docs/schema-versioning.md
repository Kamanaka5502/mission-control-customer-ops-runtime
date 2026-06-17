# Schema Versioning

Mission Control now includes Alembic-based schema versioning.

## Current revision

```text
20260617_0001
```

The initial revision creates the runtime tables for customers, workflows, operation requests, decisions, evidence items, audit events, and execution jobs.

## Apply revision

From the backend directory:

```bash
cd backend
python -m pip install -r requirements.txt
python -m alembic upgrade head
```

With an external database URL:

```bash
cd backend
DATABASE_URL=<database url> python -m alembic upgrade head
```

## Runtime version endpoint

```text
GET /schema-version
```

The endpoint reports expected head, observed database revision when available, migration-managed status, and whether the observed revision matches expected head.

## Change policy

New table or column changes should be introduced with a new Alembic revision.
