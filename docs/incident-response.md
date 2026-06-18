# Incident Response Profile

This document defines the minimum incident-response posture for Mission Control validation.

## Severity guide

```text
critical: database unavailable, auth boundary failure, protected action released incorrectly
warning: schema drift, proof verification failure, receipt verification failure
info: pending review accumulation, refusal events present, local runtime anomaly
```

## First checks

Run:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/schema-version
curl http://localhost:8000/ops/monitoring
```

## Evidence to capture

Capture:

- timestamp
- correlation id
- request id
- tenant id
- actor id
- endpoint and method
- response status
- request lifecycle status
- decision outcome
- receipt verification result
- proof bundle verification result
- audit ledger verification result

## Containment guidance

For runtime uncertainty:

1. Stop executing new protected actions.
2. Preserve request ids, correlation ids, and audit events.
3. Export proof bundles for affected requests when available.
4. Verify receipts, proof bundles, and audit ledgers.
5. Review ingress, tenant, actor, and auth-key configuration.
6. Re-enable execution only after the failed check is identified and corrected.

## Recovery validation

Before declaring recovery:

- `/ready` returns ready
- `/schema-version` reports expected head or an approved migration state
- `/ops/monitoring` reports no critical alerts
- affected request receipts verify
- affected proof bundles verify
- affected audit ledgers verify
- no duplicate execution was recorded for the same request

## Claim boundary

This profile is a repository validation runbook. It does not replace customer incident-response policy, legal hold requirements, security operations escalation, or regulated evidence-retention obligations.
