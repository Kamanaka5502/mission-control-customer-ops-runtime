# Evidence Integrity

Mission Control captures an evidence manifest hash whenever evidence is attached to a request.

## Purpose

Evidence can materially change how an operational request is interpreted. The evidence manifest gives reviewers a stable digest of the evidence set attached to a request at a material point in time.

This helps reviewers answer:

```text
Which evidence items were attached?
Did the evidence set change after capture?
Can replay and receipt work bind to a stable evidence manifest?
```

## Implemented behavior

When `POST /ops/evidence` succeeds, the runtime records an `evidence_manifest_captured` audit event containing:

- `hash_algorithm`
- `manifest_hash`
- manifest version
- evidence item count
- canonical evidence item fields

The manifest hash is generated from deterministic JSON serialization using SHA-256.

## Verification endpoint

Use:

```text
GET /ops/requests/{request_id}/integrity
```

The endpoint returns:

- captured evidence manifest hash
- current evidence manifest hash
- whether the captured and current manifest hashes match
- evidence item count
- overall integrity status

Requests with no evidence attached can still verify when the request snapshot matches and the current manifest is empty.

## Claim boundary

This is evidence-manifest integrity, not a complete evidence-custody system. Full production evidence custody still requires signed receipts, external verification, tamper-evident audit storage, retention policy, and customer-approved storage controls.
