# Threat Model

This threat model tracks the security and operational risks relevant to Mission Control as a customer-operations execution-control runtime.

The model is intentionally explicit about remaining limitations. A threat is not considered closed until the control exists in code, tests cover it, and operational documentation explains it.

## Scope

In scope:

- customer request intake
- evidence attachment
- runtime evaluation
- review actions
- controlled execution
- receipts
- replay
- audit trail
- tenant-scoped access
- deployment configuration
- proof export

Out of scope:

- full Elyria/VERITA kernel custody
- regulated legal, medical, or financial decision authority
- customer production certification before external approval
- third-party connector internals beyond allowlist and boundary checks

## Threat register

| Threat | Impact | Control target | Test target | Remaining limitation |
|---|---|---|---|---|
| Malicious requester | Unsafe or unauthorized request enters workflow | Auth, RBAC, request validation, evidence requirements | requester cannot approve or execute | Full auth/RBAC roadmap still required |
| Compromised reviewer | Reviewer approves unsafe request | Segregation of duties, audit events, final execution re-check | reviewer cannot execute without permission | Final execution re-check roadmap still required |
| Compromised executor | Executor releases unauthorized effect | Execution guard, idempotency, final checks, allowlist | executor cannot approve own request; stale approval refuses | Expanded executor controls still required |
| Malicious admin | Admin changes config or bypasses gates | Audited admin actions, least privilege, config validation | admin action creates audit event | Admin management surface still roadmap |
| Tenant data leakage | Tenant A sees Tenant B data | Tenant-scoped authorization on every object | tenant A cannot read tenant B request | Full object coverage must be verified |
| Cross-tenant replay | Tenant A replays Tenant B proof | Tenant-scoped receipt and replay retrieval | tenant A cannot replay tenant B receipt | Full proof-store tenant scope still required |
| Forged receipt | External party trusts fake proof | Canonical digest, signing key, signature verification | tampered receipt fails verification | Receipt signing roadmap still required |
| Edited audit event | Audit history becomes unreliable | Hash-chained append-only ledger | audit ledger detects edit | Hash-chain ledger roadmap still required |
| Deleted audit event | Missing event breaks custody | Previous-event hash chain | audit ledger detects delete | Hash-chain ledger roadmap still required |
| Reordered audit event | Sequence manipulation hides actions | Sequence and previous hash validation | broken chain detected | Hash-chain ledger roadmap still required |
| Stale evidence | Old evidence supports unsafe decision | Evidence freshness and expiry status | expired evidence fails closed | Evidence integrity roadmap still required |
| Revoked authority | Removed authority still executes | Final authority re-check | revoked authority refuses execution | Final authority model still required |
| Duplicate execution | Duplicate side effects | Idempotency key and execution log | duplicate execution idempotent | Idempotency roadmap still required |
| Replay attack | Sensitive endpoint reused | Replay protection on sensitive endpoints | replay endpoint cannot mutate state | Replay protection roadmap still required |
| Poisoned evidence | False evidence changes decision | Evidence validation, digest, revocation | tampered evidence fails verification | Evidence manifest roadmap still required |
| Compromised signing key | Receipts can be forged | Key ID, rotation, revocation, audit event | key rotation creates audit event | Key management roadmap still required |
| Broken connector | External connector executes wrong action | Connector allowlist, dry-run, timeout, compensating action | connector not allowlisted refuses | Connector boundary roadmap still required |
| Bypass attempt | Direct API route bypasses gate | Auth, RBAC, protected routes, final guard | protected route rejects unauthenticated mutation | Full auth roadmap still required |
| Unsafe production config | Deployment starts in weak mode | Fail-fast production settings | production startup refuses unsafe defaults | Existing config validation should continue expanding |
| Missing deployment evidence | Claims cannot be verified | Deployment evidence template and readiness checker | deployment readiness package present | External evidence required for production certification |

## Current controls already present

- Runtime decisions are explicit.
- `REFUSE` blocks protected effects.
- Controlled execution requires lifecycle permission.
- Production mode requires trusted ingress.
- Production mode requires tenant header.
- Production settings reject unsafe local database configuration.
- Defensive response headers are installed.
- CI and CodeQL run on pull requests.
- Release and deployment evidence templates exist.

## Required next controls

- authentication
- RBAC
- complete tenant-scoped authorization
- immutable request snapshots
- evidence manifest integrity
- signed receipts
- external receipt verifier
- tamper-evident audit ledger
- persistent proof store
- Postgres CI
- API rate limiting and body limits
- execution idempotency and final checks
- key rotation and revocation
- incident response procedures

## Review cadence

Update this threat model when:

- a new protected route is added
- a new runtime object is persisted
- a new proof artifact is introduced
- auth or RBAC rules change
- tenant isolation rules change
- signing or key-management behavior changes
- deployment assumptions change
