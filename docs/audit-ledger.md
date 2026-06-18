# Tamper-Evident Audit Ledger

Mission Control records audit events with a hash-chain ledger marker inside each audit event detail.

## Purpose

The audit ledger helps reviewers detect whether recorded audit events were edited or deleted after capture.

Each audit event records:

- `hash_algorithm`
- `previous_hash`
- `event_hash`

The event hash is calculated from the event id, request id, event type, actor, non-ledger detail payload, and previous hash.

## Runtime verification endpoint

Use:

```text
GET /ops/requests/{request_id}/audit/verify
```

The endpoint returns:

- `valid`
- event count
- head hash
- per-event failure details when verification fails

## Standalone verifier

Use:

```bash
python scripts/verify_audit_ledger.py
```

For a single request:

```bash
python scripts/verify_audit_ledger.py --request-id REQ-123
```

## Tamper behavior

The verifier detects:

- edited audit detail fields
- edited actor, event type, request id, or event id
- deleted events when the deletion breaks a later event's `previous_hash`

## Claim boundary

This is a repository-level tamper-evident audit chain. It is not external notarization, immutable storage, WORM retention, or production certification. Production deployment still requires customer-approved database controls, retention policy, backup policy, access controls, and external audit requirements.
