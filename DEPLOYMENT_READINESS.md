# Deployment Readiness

Mission Control is a production-candidate customer-operations runtime pattern. This file defines the readiness gates required before the repository is represented as customer-deployable or production certified.

## Current readiness status

Status: **repository-hardened, not production-certified**.

The repository currently demonstrates an operational runtime with request intake, evaluation, review, controlled execution, receipt, replay, audit trail, dashboard, CI, CodeQL, migration path, production setting validation, trusted-ingress requirement, and tenant-header enforcement in production mode.

The repository still requires additional controls before customer deployment or production certification claims are appropriate.

## Production-candidate architecture

```text
Client / Dashboard
    |
    v
Trusted Ingress / Gateway
    |
    v
Authenticated API Boundary
    |
    +--> Tenant Resolution
    +--> RBAC Permission Check
    +--> Request Intake
    +--> Evidence Binding
    +--> Snapshot Creation
    +--> Runtime Policy Gate
    +--> Human or Machine Review
    +--> Final Execution Guard
    +--> Receipt Signing
    +--> Replay Verification
    +--> Tamper-Evident Audit Ledger
    |
    v
Persistent Proof Store / PostgreSQL
```

## Implemented controls

- Request intake API
- Runtime decision outcomes: `ADMIT`, `HOLD`, `ESCALATE`, `REFUSE`
- Review action API
- Controlled execution gate
- No protected effect on `REFUSE`
- Persisted receipt endpoint
- Persisted replay endpoints
- Audit trail endpoint
- Metrics endpoint
- Dashboard API and frontend
- Correlation IDs
- Schema version endpoint
- Alembic migration path
- Docker Compose profiles
- Production setting validation
- Production refusal for unsafe local database configuration
- Production trusted-ingress requirement
- Production tenant-header requirement
- Defensive response headers
- Explicit CORS configuration for production mode
- CI workflow
- CodeQL workflow
- Dependabot configuration
- Release checklist
- Deployment evidence template
- Security policy
- Contribution guide

## Candidate controls still required

The following controls are required before all-A production-candidate claims are complete:

- real authentication
- RBAC enforcement
- complete tenant-scoped authorization across every object
- immutable request snapshots
- evidence manifest integrity
- signed receipts
- external receipt verifier
- tamper-evident audit ledger
- persistent proof bundle store
- PostgreSQL CI and production profile
- API rate limiting and body limits
- execution idempotency and final pre-execution checks
- production key management and key rotation
- monitoring and incident-response procedures
- deployment readiness checker
- threat model completion and test mapping

## Required environment variables

The production deployment must explicitly define at least:

- `APP_ENV=production`
- `DATABASE_URL` using a managed PostgreSQL database
- `REQUIRE_TENANT_HEADER=true`
- `REQUIRE_TRUSTED_INGRESS=true`
- `CORS_ALLOW_ORIGINS` with approved origins only
- signing-key configuration once receipt signing is implemented
- auth-provider or token configuration once authentication is implemented

## Database requirements

Production deployment requires:

- PostgreSQL or equivalent managed relational database
- migration execution before app startup
- least-privilege database user
- backup and restore procedure
- migration rollback plan
- database readiness probe
- retention policy for audit and proof records

SQLite is permitted for local development only.

## Auth and RBAC requirements

Before customer deployment, the runtime must require authentication for all protected mutation and export paths.

Required role families:

- requester
- reviewer
- executor
- auditor
- admin
- service account
- tenant admin

Each role must have explicit endpoint permissions and tests proving that unauthorized roles fail closed.

## Tenant isolation requirements

Every runtime object that can affect customer state must carry a tenant identifier and enforce tenant-scoped access.

Tenant A must not read, replay, export, or execute Tenant B objects.

## Receipt and audit requirements

Before stronger proof-chain claims are made, Mission Control must implement:

- immutable request snapshot digest
- evidence manifest digest
- canonical receipt digest
- receipt signature
- key ID
- external receipt verifier
- append-only audit hash chain
- audit ledger verifier

## Monitoring requirements

Production candidate monitoring must include alerts or equivalent operational signals for:

- failed receipt verification
- failed replay verification
- failed audit ledger verification
- repeated refusal or escalation spikes
- cross-tenant access attempts
- bypass attempts
- execution failures
- receipt signing failures
- key rotation events

## Rollback requirements

A deployment candidate must document:

- application rollback
- database migration rollback
- signing-key rotation and recovery
- emergency halt
- incident response
- tenant onboarding and offboarding
- audit export handoff

## Go / no-go checklist

Go requires:

- all required configuration set explicitly
- migrations applied successfully
- readiness endpoint healthy
- CI and CodeQL green
- protected-route tests passing
- tenant isolation tests passing
- receipt/replay/audit tests passing
- rollback path documented
- deployment evidence recorded

No-go if:

- auth is disabled in production
- default or missing signing keys are present after receipt signing is implemented
- tenant enforcement is disabled
- unsafe local database is used in production
- audit or receipt verification fails
- required environment variables are missing
- customer security approval or external audit is required but not complete

## External audit checklist

External review should inspect:

- auth and RBAC enforcement
- tenant isolation
- request snapshot immutability
- evidence integrity
- receipt signing and verification
- audit ledger hash chain
- proof persistence
- production database posture
- API hardening
- key management
- deployment process
- incident response process
- claims boundary

## Production certification gate

Mission Control must not be described as production certified until one of the following is complete:

1. customer security approval for the specific deployment scope, or
2. external audit covering the implemented controls, or
3. equivalent written deployment authorization.

Until that gate is complete, use: **production-candidate operational runtime**.
