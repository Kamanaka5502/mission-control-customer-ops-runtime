from __future__ import annotations

import os
import sys

from sqlalchemy import create_engine, inspect, text

EXPECTED_SCHEMA_HEAD = "20260617_0001"
REQUIRED_TABLES = {
    "alembic_version",
    "customers",
    "workflows",
    "operation_requests",
    "decisions",
    "evidence_items",
    "audit_events",
    "execution_jobs",
}


def main() -> int:
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url.startswith("postgresql"):
        print("DATABASE_URL must use PostgreSQL for this check", file=sys.stderr)
        return 2

    engine = create_engine(database_url)
    with engine.connect() as connection:
        version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        tables = set(inspect(connection).get_table_names())

    missing = sorted(REQUIRED_TABLES - tables)
    if version != EXPECTED_SCHEMA_HEAD:
        print(f"schema version mismatch: expected={EXPECTED_SCHEMA_HEAD} observed={version}", file=sys.stderr)
        return 1
    if missing:
        print(f"missing required tables: {', '.join(missing)}", file=sys.stderr)
        return 1

    print(f"PostgreSQL schema verified at {version} with {len(REQUIRED_TABLES)} required tables")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
