# Request Snapshots

Mission Control captures a stable request snapshot when a request is first evaluated.

## Purpose

The snapshot records the material request fields used by the runtime policy gate before later review, evidence, replay, or execution activity can change operational context.

This helps reviewers answer:

```text
What exact request state did the runtime evaluate?
Has the persisted request state drifted from the evaluated state?
Can a later replay be compared against the original request posture?
```

## Implemented behavior

When `POST /ops/requests/evaluate` succeeds, the runtime records a `request_snapshot_captured` audit event containing:

- `hash_algorithm`
- `snapshot_hash`
- canonical request snapshot fields

The snapshot hash is generated from deterministic JSON serialization using SHA-256.

## Verification endpoint

Use:

```text
GET /ops/requests/{request_id}/integrity
```

The endpoint returns:

- captured request snapshot hash
- current request snapshot hash
- whether the captured and current hashes match
- current evidence manifest status
- overall integrity status

## Claim boundary

This is a repository-level integrity control. It does not by itself prove full tamper-evident audit storage, external notarization, or production certification.

The next hardening layer is to bind these snapshot hashes into signed receipts and an external verifier.
