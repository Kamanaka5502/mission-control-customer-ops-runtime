# PostgreSQL CI Coverage

Mission Control runs backend tests against two database modes:

- SQLite for fast local-compatible test coverage
- PostgreSQL for production-shaped persistence coverage

## CI job

The GitHub Actions job is:

```text
backend-postgres
```

It starts a PostgreSQL 16 service container, applies Alembic migrations, verifies the expected schema version, and runs the backend pytest suite with `DATABASE_URL` set to PostgreSQL.

## Schema verification

The CI job runs:

```bash
PYTHONPATH=. python scripts/check_postgres_ci.py
```

The script verifies:

- `DATABASE_URL` is PostgreSQL
- Alembic version matches the expected schema head
- required runtime tables exist

## Claim boundary

This closes the repository-level gap between `PostgreSQL-ready` and `PostgreSQL tested in CI`. It does not replace customer deployment testing, managed database configuration, backup validation, restore drills, or production performance testing.
