# Role-Based Access Control

Mission Control enforces role-based access at protected runtime endpoints. The Phase 2 implementation replaces broad route role checks on core operations with permission-level checks.

## Roles

| Role | Purpose |
|---|---|
| `requester` | Creates operational requests and attaches evidence. |
| `reviewer` | Reviews requests and records hold/escalate/approve/refuse decisions. |
| `executor` | Releases approved or directly admitted actions through the execution guard. |
| `auditor` | Reads requests, receipts, replays, audit logs, and dashboard state without mutation. |
| `admin` | Administrative super-role for controlled setup and operations. |
| `service_account` | Scoped machine identity for explicitly allowed machine actions. |
| `tenant_admin` | Tenant-local management role for tenant-scoped setup and oversight. |
| `operator` | Backward-compatible local-demo role. Production deployments should prefer explicit roles. |

## Permission matrix

| Permission | requester | reviewer | executor | auditor | admin | service account |
|---|---:|---:|---:|---:|---:|---:|
| `request:create` | yes | no | no | no | yes | scoped |
| `evidence:attach` | yes | no | no | no | yes | scoped |
| `request:read` | yes | yes | yes | yes | yes | scoped |
| `review:write` | no | yes | no | no | yes | no |
| `execution:run` | no | no | yes | no | yes | no |
| `receipt:read` | no | yes | no | yes | yes | scoped |
| `replay:run` | no | yes | no | yes | yes | scoped |
| `audit:read` | no | yes | no | yes | yes | scoped |
| `dashboard:read` | yes | yes | yes | yes | yes | scoped |
| `execution_job:read` | no | no | yes | yes | yes | scoped |
| `execution_job:write` | no | no | yes | no | yes | scoped |

## Fail-closed rules

- A missing or invalid bearer token fails with `401` when auth is required.
- A valid identity without permission fails with `403`.
- A requester cannot approve.
- A reviewer cannot execute without executor permission.
- An auditor cannot mutate runtime state.
- A service account cannot exceed its declared scopes.
- A service account cannot perform review actions.

## Current implementation notes

The core operations API now uses permission checks for:

- request creation
- request reads
- review actions
- controlled execution
- receipt reads
- replay runs
- audit reads
- evidence attachment
- dashboard reads

Execution job routes remain compatible with the existing operator/admin path and are tracked for follow-up executor-specific hardening.

## Production expectations

Production deployments must use explicit roles and signed bearer tokens. Header-only role selection is only for local development and demo compatibility.

See also:

- `docs/authentication.md`
- `docs/tenant-isolation.md`
- `DEPLOYMENT_READINESS.md`
