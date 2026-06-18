# Deployment Readiness

Mission Control is a production-candidate customer-operations runtime pattern. This file defines the readiness gates required before the repository is represented as customer-deployable or production certified.

## Current readiness status

Status: **repository-hardened, not production-certified**.

The repository demonstrates an operational runtime with request intake, evaluation, review, controlled execution, receipt, replay, audit trail, dashboard, CI, CodeQL, migration path, PostgreSQL CI coverage, production setting validation, trusted-ingress requirement, tenant-header enforcement, monitoring profile, incident-response documentation, key-management validation, and a deployment certification gate.

The repository still requires customer security approval, external audit approval, or equivalent written deployment authorization before production-certified claims are appropriate.

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
    +--> Monitoring Profile
    |
    v
Persistent Proof Store / PostgreSQL
```

## Implemented controls

- Request intake API
- Runtime decision outcomes: `ADMIT`, `HOLD`, `ESCALATE`, `REFUSE`
- Review action API
- Controlled execution gate
- Execution idempotency and final pre-execution checks
- No protected effect on `REFUSE`
- Persisted receipt endpoint
- Persisted replay endpoints
- Signed receipt verification
- External receipt verifier
- Audit trail endpoint
- Tamper-evident audit ledger verification
- Persistent proof bundle store
- Metrics endpoint
- Monitoring profile endpoint
- Incident-response documentation
- Dashboard API and frontend
- Correlation IDs
- Schema version endpoint
- Alembic migration path
- PostgreSQL CI coverage
- Docker Compose profiles
- Production setting validation
- Production refusal for unsafe local database configuration
- Production trusted-ingress requirement
- Production tenant-header requirement
- Authentication and RBAC
- Tenant-scoped request access
- API rate limits and body-size limits
- Production key-management validation
- Defensive response headers
- Explicit CORS configuration for production mode
- CI workflow
- CodeQL workflow
- Dependabot configuration
- Release checklist
- Deployment evidence template
- Deployment certification gate
- Security policy
- Contribution guide

## Certification controls still external

The following items are intentionally outside repository-only proof and require deployment-specific evidence:

- customer security approval, external audit approval, or equivalent written deployment authorization
- customer-approved storage, retention, backup, and restore policy
- customer-approved logging and alert routing
- customer-approved secrets/KMS/HSM policy
- customer-approved ingress and identity-provider configuration
- deployment-specific rollback approval
- production load, latency, and availability validation

## Required environment variables

The production deployment must explicitly define at least:

- `APP_ENV=production`
- `DATABASE_URL` using a managed PostgreSQL database
- `REQUIRE_TENANT_HEADER=true`
- `REQUIRE_TRUSTED_INGRESS=true`
- `AUTH_REQUIRED=true`
- `AUTH_TOKEN_SECRET` from a secret manager or deployment environment
- `RECEIPT_SIGNING_KEY_ID` with an explicit non-default key id
- `RECEIPT_SIGNING_SECRET` from a secret manager or deployment environment
- `CORS_ALLOW_ORIGINS` with approved origins only

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

Production mode requires authentication for protected runtime actions.

Required role families:

- requester
- reviewer
- executor
- auditor
- admin
- service account
- tenant admin

Each role has explicit endpoint permissions and tests proving that unauthorized roles fail closed.

## Tenant isolation requirements

Runtime objects that can affect customer state carry a tenant identifier and enforce tenant-scoped access.

Tenant A must not read, replay, export, or execute Tenant B objects.

## Receipt and audit requirements

Mission Control implements:

- immutable request snapshot digest
- evidence manifest digest
- canonical receipt digest
- receipt signature
- key ID
- external receipt verifier
- append-only audit hash chain
- audit ledger verifier
- persistent signed proof bundle verifier

## Monitoring requirements

Production candidate monitoring includes repository-level operational signals for:

- database availability
- schema version state
- request lifecycle counts
- decision outcome counts
- pending review visibility
- refusal visibility
- incident handoff fields

Customer deployment should connect these outputs to customer-approved monitoring, logging, alert routing, and incident-management tooling.

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
- monitoring endpoint available
- CI and CodeQL green
- SQLite backend tests passing
- PostgreSQL backend tests passing
- protected-route tests passing
- tenant isolation tests passing
- receipt/replay/audit/proof tests passing
- rollback path documented
- deployment evidence recorded
- certification evidence approved for the exact deployment scope

No-go if:

- auth is disabled in production
- default or missing signing keys are present
- tenant enforcement is disabled
- trusted ingress enforcement is disabled
- unsafe local database is used in production
- audit, receipt, proof, or replay verification fails
- required environment variables are missing
- customer security approval or external audit is required but not complete
- deployment certification evidence is missing or not approved

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
- monitoring and incident response
- deployment process
- claims boundary

## Production certification gate

Mission Control must not be described as production certified until one of the following is complete for the specific deployment scope:

1. customer security approval, or
2. external audit covering the implemented controls, or
3. equivalent written deployment authorization.

Use the repository gate for code-level readiness:

```bash
python scripts/certify_deployment.py --repo-check-only
```

Use the certification gate only with completed deployment evidence:

```bash
python scripts/certify_deployment.py --certify --evidence-file <completed-evidence-file>
```

Until that gate is complete, use: **production-candidate operational runtime**.
