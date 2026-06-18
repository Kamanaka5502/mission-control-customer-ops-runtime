# Persistent Proof Store

Mission Control can export and persist request-level proof bundles as JSON files.

## Purpose

A proof bundle gives reviewers one exportable object that ties together the runtime evidence trail for a request.

The bundle includes:

- request snapshot
- evidence manifest
- decision record
- signed receipt
- receipt verification result
- same-condition replay result
- audit ledger verification result
- integrity status
- proof hash

## API

Export and persist a proof bundle:

```text
POST /ops/requests/{request_id}/proof-bundle
```

Read a stored bundle:

```text
GET /ops/requests/{request_id}/proof-bundle
```

Verify a stored bundle:

```text
GET /ops/requests/{request_id}/proof-bundle/verify
```

## Storage path

By default, proof bundles are stored under:

```text
var/proof_store
```

Override with:

```bash
PROOF_STORE_PATH=/path/to/proof-store
```

## Standalone verifier

Use:

```bash
python scripts/verify_proof_bundle.py var/proof_store/REQ-123.proof.json
```

The verifier checks:

- proof hash
- receipt signature
- audit ledger validity
- request snapshot match
- evidence manifest match
- same-condition replay match

## Claim boundary

This is a repository-level proof export and local proof store. It is not customer-approved evidence retention, external notarization, immutable storage, or production certification. Production deployment still requires customer-approved storage, access control, retention, backup, and incident-response procedures.
