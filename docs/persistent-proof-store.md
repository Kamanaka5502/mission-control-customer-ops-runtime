# Persistent Proof Store

Mission Control can export and persist request-level proof bundles as JSON files.

## Purpose

A proof bundle gives reviewers one exportable object that ties together the runtime evidence trail for a request.

The bundle includes:

- request snapshot
- evidence manifest
- decision record
- originally issued signed receipt
- receipt verification result
- same-condition replay result
- audit event records
- audit ledger verification result
- integrity status
- proof hash
- proof signature

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

Proof bundle file names are derived from a SHA-256 digest of the request id. Request ids used for proof-store paths are restricted to safe filename characters.

## Standalone verifier

Use:

```bash
python scripts/verify_proof_bundle.py var/proof_store/<proof-bundle-file>.proof.json
```

The verifier checks:

- proof hash
- proof signature
- receipt signature
- receipt consistency with the stored decision token
- request snapshot hash
- evidence manifest hash
- recomputed audit ledger validity
- request snapshot match
- evidence manifest match
- same-condition replay match

## Claim boundary

This is a repository-level proof export and local proof store. It is not customer-approved evidence retention, external notarization, immutable storage, or production certification. Production deployment still requires customer-approved storage, access control, retention, backup, and incident-response procedures.
