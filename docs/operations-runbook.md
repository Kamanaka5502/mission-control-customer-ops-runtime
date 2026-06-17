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
NEXT_PUBLIC_API_BASE=https://api.example.com \
CORS_ALLOW_ORIGINS=https://app.example.com \
docker compose -f docker-compose.prod.yml up --build
```

Run the API behind authenticated ingress. Production requests must include verified ingress identity, actor role, and tenant id after authentication and tenant resolution.

## Schema versioning

Apply the current schema revision from the backend directory:

```bash
python -m alembic upgrade head
```

Runtime schema state is available at:

```text
GET /schema-version
```

## Health checks

Liveness:

```bash
curl http://localhost:8000/health
```

Readiness:

```bash
curl http://localhost:8000/ready
```

`/health` confirms the service process is available. `/ready` confirms the application can reach its database.

## Release checklist

Before external deployment, verify:

- backend migrations apply cleanly
- backend tests pass
- frontend build passes
- production env vars are set
- API is behind authenticated ingress
- tenant id is resolved upstream
- CORS origins are explicitly listed for the deployed frontend
- logs preserve correlation ids
- closed/REFUSE requests cannot release protected action
- dependency update alerts are enabled
