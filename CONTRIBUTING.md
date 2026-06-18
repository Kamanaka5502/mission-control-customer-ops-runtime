# Contributing

Mission Control changes should preserve the runtime's core invariant:

```text
No protected action should execute unless the request has been admitted, tenant-scoped, and allowed by the current lifecycle state.
```

## Development flow

1. Create a branch from `main`.
2. Keep changes scoped.
3. Add or update tests for behavior changes.
4. Run local validation before opening a pull request.
5. Use the pull request template to document boundary impact.

## Local validation

Backend:

```bash
cd backend
python -m pip install -r requirements.txt
DATABASE_URL=sqlite:////tmp/mission_control_contrib.db python -m alembic upgrade head
DATABASE_URL=sqlite:////tmp/mission_control_contrib.db PYTHONPATH=. python -m pytest -q
```

Frontend:

```bash
cd frontend
npm ci
npm run build
```

Production compose config:

```bash
POSTGRES_PASSWORD=local-check \
NEXT_PUBLIC_API_BASE=https://api.example.com \
CORS_ALLOW_ORIGINS=https://app.example.com \
docker compose -f docker-compose.prod.yml config
```

## Boundary review expectations

Changes that touch execution, tenant isolation, evidence, replay, ingress identity, actor role handling, or database schema need explicit review notes.

Do not weaken fail-closed behavior without documenting the reason and adding tests.

## Documentation expectations

Update runbooks, release checklists, or evidence templates when operational behavior changes.
