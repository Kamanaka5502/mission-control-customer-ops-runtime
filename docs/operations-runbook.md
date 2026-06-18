# Operations Runbook

Mission Control is a governed customer-operations runtime. This runbook defines the minimum operating posture for local validation and controlled deployment.

## Local validation

Backend:

```bash
cd backend
python -m pip install -r requirements.txt
python -m alembic upgrade head
PYTHONPATH=. python -m pytest -q
```

Frontend:

```bash
cd frontend
npm ci
npm run build
```

Full local runtime:

```bash
docker compose up --build
```

## Production-shaped runtime

Use the production compose profile only with required environment variables supplied:

```bash
POSTGRES_PASSWORD=<strong value> \
AUTH_TOKEN_SECRET=<strong value> \
RECEIPT_SIGNING_KEY_ID=<explicit key id> \
RECEIPT_SIGNING_SECRET=<strong value> \
NEXT_PUBLIC_API_BASE=https://api.example.com \
CORS_ALLOW_ORIGINS=https://app.example.com \
docker compose -f docker-compose.prod.yml up --build
```

Run the API behind authenticated ingress. Production requests must include verified ingress identity, actor role, and tenant id after authentication and tenant resolution.

## Production boundary posture

The runtime intentionally fails closed when `APP_ENV=production` is set without required deployment controls:

- `DATABASE_URL` must be present and must not use SQLite
- `REQUIRE_TENANT_HEADER` must be enabled
- `REQUIRE_TRUSTED_INGRESS` must be enabled
- `AUTH_REQUIRED` must be enabled
- auth and signing keys must be non-default
- `CORS_ALLOW_ORIGINS` must be explicit and must not use localhost origins

The production compose profile binds API and frontend ports to localhost, requires explicit CORS origins, runs service containers as non-root users, blocks privilege escalation, and uses read-only containers with temporary writable storage.

## Schema versioning

Apply the current schema revision from the backend directory:

```bash
python -m alembic upgrade head
```

Runtime schema state is available at:

```text
GET /schema-version
```

## Health and monitoring checks

Liveness:

```bash
curl http://localhost:8000/health
```

Readiness:

```bash
curl http://localhost:8000/ready
```

Monitoring profile:

```bash
curl http://localhost:8000/ops/monitoring
```

`/health` confirms the service process is available. `/ready` confirms the application can reach its database. `/ops/monitoring` returns runtime counts, alert checks, dependency probes, and incident handoff fields.

## Incident response

Use `docs/incident-response.md` for incident triage. Minimum evidence to preserve:

- request id
- correlation id
- tenant id
- actor id
- timestamp
- current monitoring profile response
- audit events for affected requests
- receipt and proof verification results

## Release checklist

Before external deployment, verify:

- backend migrations apply cleanly
- backend tests pass
- frontend build passes
- production env vars are set
- API is behind authenticated ingress
- tenant id is resolved upstream
- CORS origins are explicitly listed for the deployed frontend
- service containers run as non-root users
- public traffic cannot directly set trusted identity headers
- logs preserve correlation ids
- closed/REFUSE requests cannot release protected action
- monitoring profile returns expected shape
- incident-response runbook is reviewed
- dependency update alerts are enabled
